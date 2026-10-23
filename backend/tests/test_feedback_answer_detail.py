import copy
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy.dialects import postgresql
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from database.models import Feedback
from routes import feedback as routes
from services.feedback_questions import answer_detail, load_feedback_questions


def question(identifier='q', text='Původní otázka', kind='yesno'):
    return {'id': identifier, 'question_text': text, 'question_type': kind,
            'source': 'institution', 'is_required': False}


class FeedbackDetailTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.inst = uuid.uuid4()
        self.feedback = NS(id=uuid.uuid4(), reservation_id=uuid.uuid4(), program_id=uuid.uuid4(),
            institution_id=self.inst, status='pending', questions_snapshot=None, answers={},
            additional_comments='Více\nřádků', overall_rating=4, would_recommend=False,
            submitted_at=None, created_at=datetime.now(timezone.utc))
        self.reservation = NS(school_name='Test škola', date='2026-10-23')
        self.program = NS(name_cs='Program', institution_id=self.inst,
                          feedback_enabled=True, feedback_questions=[])
        self.institution = NS(name='Muzeum', logo_url=None)
        self.db = AsyncMock()
        self.user = {'institution_id': str(self.inst), 'role': 'admin'}

    def detail_result(self):
        self.db.execute.return_value = NS(one_or_none=lambda: (
            self.feedback, self.reservation, self.program))

    async def test_snapshot_freezes_on_first_open_and_survives_edit(self):
        self.db.execute.return_value = NS(one_or_none=lambda: (
            self.feedback, self.reservation, self.program, self.institution))
        with patch.object(routes, 'load_feedback_questions', AsyncMock(return_value=[question()])) as load:
            first = await routes.get_public_feedback_form('test', db=self.db)
            load.return_value = [question(text='Nové znění')]
            second = await routes.get_public_feedback_form('test', db=self.db)
            self.assertEqual(first['questions'], second['questions'])
            self.assertEqual(load.await_count, 1)
            self.assertEqual(self.db.commit.await_count, 2)
        sql = str(self.db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
        self.assertIn('FOR UPDATE OF feedbacks', sql)
        self.assertIn('reservations.institution_id = feedbacks.institution_id', sql)

    async def test_empty_snapshot_is_not_replaced_with_new_questions(self):
        self.feedback.questions_snapshot = []
        self.db.execute.return_value = NS(one_or_none=lambda: (
            self.feedback, self.reservation, self.program, self.institution))
        with patch.object(routes, 'load_feedback_questions', AsyncMock()) as load:
            data = await routes.get_public_feedback_form('test', db=self.db)
            self.assertEqual(data['questions'], [])
            load.assert_not_awaited()

    async def test_detail_has_full_comment_false_unanswered_and_original_wording(self):
        self.feedback.questions_snapshot = [question(), question('empty', kind='text')]
        self.feedback.answers = {'q': False}
        self.feedback.status = 'submitted'
        self.detail_result()
        with patch.object(routes, 'load_feedback_questions', AsyncMock()) as load:
            result = await routes.get_feedback_detail(str(self.feedback.id), db=self.db, current_user=self.user)
            load.assert_not_awaited()
        self.assertEqual(result.additional_comments, 'Více\nřádků')
        self.assertEqual(result.questions_version, 'snapshot')
        self.assertIs(result.question_answers[0]['answer'], False)
        self.assertIsNone(result.question_answers[1]['answer'])
        self.assertEqual(result.question_answers[0]['question_text'], 'Původní otázka')
        self.assertNotIn('token', result.model_dump())

    async def test_legacy_does_not_invent_original_wording_or_missing_answers(self):
        self.feedback.answers = {'q': 'text', 'deleted': False}
        self.detail_result()
        with patch.object(routes, 'load_feedback_questions', AsyncMock(return_value=[question(), question('new')])):
            result = await routes.get_feedback_detail(str(self.feedback.id), db=self.db, current_user=self.user)
        self.assertEqual(result.questions_version, 'legacy')
        self.assertEqual([q['wording_status'] for q in result.question_answers], ['current', 'missing'])
        self.assertEqual(len(result.question_answers), 2)
        self.assertIsNone(self.feedback.questions_snapshot)
        self.db.commit.assert_not_awaited()

    async def test_detail_not_found_and_scope_and_roles(self):
        self.db.execute.return_value = NS(one_or_none=lambda: None)
        with self.assertRaises(HTTPException) as error:
            await routes.get_feedback_detail(str(uuid.uuid4()), db=self.db, current_user=self.user)
        self.assertEqual(error.exception.status_code, 404)
        sql = str(self.db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
        self.assertIn('feedbacks.institution_id =', sql)
        self.assertIn('reservations.institution_id =', sql)
        self.assertIn('programs.institution_id = feedbacks.institution_id', sql)
        for role in ('lecturer', 'user'):
            with self.assertRaises(HTTPException) as error:
                await routes.get_feedback_detail('test', db=self.db, current_user={**self.user, 'role': role})
            self.assertEqual(error.exception.status_code, 403)

    async def test_submit_preserves_snapshot_and_rejects_repeated_submission(self):
        self.feedback.questions_snapshot = [question()]
        before = copy.deepcopy(self.feedback.questions_snapshot)
        self.db.execute.return_value = NS(scalar_one_or_none=lambda: self.feedback)
        data = routes.FeedbackSubmission(answers={'q': False}, additional_comments='Komentář')
        await routes.submit_public_feedback('test', data, db=self.db)
        self.assertEqual(self.feedback.questions_snapshot, before)
        self.assertIs(self.feedback.answers['q'], False)
        self.assertEqual(self.feedback.status, 'submitted')
        self.assertIn('FOR UPDATE', str(self.db.execute.call_args.args[0].compile(dialect=postgresql.dialect())))
        with self.assertRaises(HTTPException) as error:
            await routes.submit_public_feedback('test', data, db=self.db)
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(self.db.commit.await_count, 1)

    async def test_old_open_form_must_reload_unknown_ids_rejected(self):
        self.db.execute.return_value = NS(scalar_one_or_none=lambda: self.feedback)
        data = routes.FeedbackSubmission(answers={'unknown': 'text'})
        with self.assertRaises(HTTPException) as error:
            await routes.submit_public_feedback('test', data, db=self.db)
        self.assertEqual(error.exception.status_code, 409)
        self.feedback.questions_snapshot = []
        with self.assertRaises(HTTPException) as error:
            await routes.submit_public_feedback('test', data, db=self.db)
        self.assertEqual(error.exception.status_code, 422)
        self.db.commit.assert_not_awaited()

    async def test_question_sources_and_foreign_program_guard(self):
        self.db.execute.return_value = NS(scalars=lambda: NS(all=lambda: [
            NS(id='q', question_text='Instituce', question_type='text', is_required=True)]))
        self.program.feedback_questions = [{'id': 'p', 'question': 'Program', 'type': 'scale'}]
        definitions = await load_feedback_questions(self.db, self.inst, self.program)
        self.assertEqual([q['source'] for q in definitions], ['institution', 'program'])
        self.assertEqual(definitions[1]['id'], 'prog_p')
        self.assertEqual(definitions[1]['question_type'], 'rating')
        self.program.institution_id = uuid.uuid4()
        self.assertEqual(len(await load_feedback_questions(self.db, self.inst, self.program)), 1)

    def test_values_and_unknown_answer_are_not_discarded(self):
        rows = answer_detail({'q': False, 'unknown': 0}, [question(), question('empty')], True)
        self.assertEqual([row['answer'] for row in rows], [False, None, 0])

    async def test_real_database_roundtrip_retains_wording_and_answers(self):
        engine = create_engine('sqlite:///:memory:')
        Feedback.__table__.create(engine)
        identifier = uuid.uuid4()
        try:
            with Session(engine) as session:
                session.add(Feedback(id=identifier, institution_id=self.inst,
                    reservation_id=uuid.uuid4(), token='synthetic', status='pending',
                    questions_snapshot=[question()]))
                session.commit()
            with Session(engine) as session:
                class Adapter:
                    async def execute(self, statement):
                        return session.execute(statement)

                    async def commit(self):
                        session.commit()

                await routes.submit_public_feedback('synthetic', routes.FeedbackSubmission(
                    answers={'q': False}, additional_comments='Úplný komentář'), db=Adapter())
            with Session(engine) as session:
                stored = session.get(Feedback, identifier)
                self.assertEqual(stored.questions_snapshot, [question()])
                self.assertEqual(stored.answers, {'q': False})
                self.assertEqual(stored.additional_comments, 'Úplný komentář')
                self.assertEqual(stored.status, 'submitted')
        finally:
            engine.dispose()
