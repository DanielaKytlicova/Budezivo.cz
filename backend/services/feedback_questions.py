"""Question definitions shared by public forms and the private answer detail."""
from sqlalchemy import select
from database.models import FeedbackQuestion


async def load_feedback_questions(db, institution_id, program, include_inactive=False):
    query = select(FeedbackQuestion).where(FeedbackQuestion.institution_id == institution_id)
    if not include_inactive:
        query = query.where(FeedbackQuestion.is_active == True)
    questions = (await db.execute(query.order_by(
        FeedbackQuestion.display_order, FeedbackQuestion.id
    ))).scalars().all()
    definitions = [{
        'id': str(q.id), 'question_text': q.question_text,
        'question_type': q.question_type, 'is_required': q.is_required,
        'source': 'institution',
    } for q in questions]
    if (program and str(program.institution_id) == str(institution_id)
            and (include_inactive or program.feedback_enabled)):
        for question in program.feedback_questions or []:
            if question.get('question'):
                definitions.append({
                    'id': f"prog_{question.get('id', '')}",
                    'question_text': question['question'],
                    'question_type': 'rating' if question.get('type') == 'scale' else question.get('type', 'text'),
                    'is_required': False, 'source': 'program',
                })
    return definitions


def answer_detail(answers, definitions, historical):
    """Never infer old unanswered questions from today's configuration."""
    answers = answers or {}
    rows = []
    known = set()
    for question in definitions:
        identifier = question['id']
        known.add(identifier)
        if not historical and identifier not in answers:
            continue
        rows.append({**question, 'answer': answers.get(identifier),
                     'wording_status': 'snapshot' if historical else 'current'})
    for identifier, value in answers.items():
        if identifier not in known:
            rows.append({'id': identifier, 'question_text': 'Původní znění otázky není dostupné',
                         'question_type': 'unknown', 'source': 'unknown',
                         'answer': value, 'wording_status': 'missing'})
    return rows
