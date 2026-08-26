import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "frontend" / "src" / "pages" / "admin" / "UnifiedAvailabilityPage.js"


class ProgramBlockGroupEditUiTests(unittest.TestCase):
    def test_program_blocks_are_grouped_as_ranges(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("date_from: e.date", source)
        self.assertIn("date_to: e.date", source)
        self.assertIn("exceptions: []", source)
        self.assertIn("group.exceptions.push", source)
        self.assertIn("const nextDateStr = (dateStr) =>", source)
        self.assertIn("const sameProgramSet = (a = [], b = []) =>", source)
        self.assertIn("nextDateStr(previous.date_to) === group.date", source)
        self.assertIn("previous.date_to = group.date", source)
        self.assertIn("group.date_to !== group.date_from", source)

    def test_grouped_program_blocks_open_the_edit_dialog(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("const [editingProgramBlockGroup, setEditingProgramBlockGroup]", source)
        self.assertIn("const openProgramBlockEditDialog = (group) =>", source)
        self.assertIn("setEditingProgramBlockGroup(group)", source)
        self.assertIn("date_from: group.date_from", source)
        self.assertIn("date_to: group.date_to", source)
        self.assertIn("onClick={() => openProgramBlockEditDialog(group)}", source)
        self.assertIn("Upravit programovou blokaci", source)
        self.assertIn("Upraví celou blokaci včetně všech dnů a programů.", source)
        self.assertIn("pblock-edit-days", source)
        self.assertIn("deleteProgramBlockDay(date)", source)
        self.assertIn("delete-program-block-group", source)

    def test_edit_replaces_the_original_exception_rows(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("editingProgramBlockGroup?.exceptionIds?.length", source)
        self.assertIn("editingProgramBlockGroup.exceptionIds.map(exceptionId =>", source)
        self.assertIn("axios.delete(`${API}/availability-unified/exceptions/${exceptionId}`)", source)
        self.assertIn("axios.post(`${API}/availability-unified/exceptions`,", source)
        self.assertIn("Programová blokace aktualizována", source)

    def test_calendar_restore_finds_all_day_or_overlapping_exception(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("const findExceptionForSlot = () =>", source)
        self.assertIn("if (!e.start_time && !e.end_time) return true", source)
        self.assertIn("slotStart < exceptionEnd && slotEnd > exceptionStart", source)
        self.assertIn("const match = findExceptionForSlot()", source)

    def test_program_block_can_be_deleted_as_group_or_by_day(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("const removeProgramBlockExceptionIds = async (exceptionIds, successMessage) =>", source)
        self.assertIn("const deleteProgramBlockGroup = async () =>", source)
        self.assertIn("const deleteProgramBlockDay = async (date) =>", source)
        self.assertIn("editingProgramBlockGroup.exceptionIds", source)
        self.assertIn("editingProgramBlockGroup.exceptions || []", source)
        self.assertIn("Programová blokace smazána", source)
        self.assertIn("Den blokace smazán", source)


if __name__ == "__main__":
    unittest.main()
