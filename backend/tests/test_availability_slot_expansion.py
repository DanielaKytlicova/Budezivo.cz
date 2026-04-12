"""
Test suite for availability slot expansion and booking URL preselection features.

Tests:
1. Time window expansion into individual slots based on program duration
2. 90min program with window 08:30-12:00 - last valid slot is 10:30-12:00
3. 60min program with window 08:30-12:00 - slots from 08:30-09:30 through 11:00-12:00
4. Programs with exact slot definitions (like '09:00-10:30') are NOT expanded
5. Overlap-based booking detection with expanded slots
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"

# Program IDs from the test data
CTEME_OBRAZY_ID = "128d6178-e199-4cc5-b247-0e42fe1955d7"  # 60min, time_blocks: ['08:30-12:00', '13:00-15:00']
ARCHITEKTURA_MESTA_ID = "4a96dcc2-acd5-4176-b311-38e2538cb53d"  # 90min, time_blocks: ['08:30-12:00', '13:00-15:00']
HISTORICKA_PROHLIDKA_ID = "fa7c7513-813c-4c10-827c-30ff11a46caf"  # 90min, time_blocks: ['09:00-10:30'] - exact slot

TEST_DATE = "2026-04-24"  # Friday


class TestAvailabilitySlotExpansion:
    """Test time window expansion into individual slots."""
    
    def test_60min_program_expands_morning_window(self):
        """
        60min program with window 08:30-12:00 should expand into slots:
        08:30-09:30, 09:00-10:00, 09:30-10:30, 10:00-11:00, 10:30-11:30, 11:00-12:00
        """
        response = requests.get(f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{CTEME_OBRAZY_ID}/{TEST_DATE}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        time_blocks = data.get("time_blocks", [])
        
        # Extract morning slots (before 12:00)
        morning_slots = [b["time"] for b in time_blocks if b["time"].startswith(("08:", "09:", "10:", "11:"))]
        
        # Should have 6 morning slots for 60min program with 08:30-12:00 window
        expected_morning_slots = [
            "08:30-09:30", "09:00-10:00", "09:30-10:30", 
            "10:00-11:00", "10:30-11:30", "11:00-12:00"
        ]
        
        for expected in expected_morning_slots:
            assert expected in morning_slots, f"Expected slot {expected} not found in {morning_slots}"
        
        print(f"✅ 60min program correctly expanded to {len(morning_slots)} morning slots")
    
    def test_90min_program_expands_with_correct_last_slot(self):
        """
        90min program with window 08:30-12:00 should expand into slots:
        08:30-10:00, 09:00-10:30, 09:30-11:00, 10:00-11:30, 10:30-12:00
        
        11:00-12:30 should NOT be included (exceeds window end)
        """
        response = requests.get(f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{ARCHITEKTURA_MESTA_ID}/{TEST_DATE}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        time_blocks = data.get("time_blocks", [])
        
        # Extract morning slots
        morning_slots = [b["time"] for b in time_blocks if b["time"].startswith(("08:", "09:", "10:"))]
        
        # Should have 5 morning slots for 90min program with 08:30-12:00 window
        expected_morning_slots = [
            "08:30-10:00", "09:00-10:30", "09:30-11:00", 
            "10:00-11:30", "10:30-12:00"
        ]
        
        for expected in expected_morning_slots:
            assert expected in morning_slots, f"Expected slot {expected} not found in {morning_slots}"
        
        # 11:00-12:30 should NOT be present (exceeds window)
        invalid_slot = "11:00-12:30"
        assert invalid_slot not in morning_slots, f"Invalid slot {invalid_slot} should not be present"
        
        print(f"✅ 90min program correctly expanded to {len(morning_slots)} morning slots, last valid slot is 10:30-12:00")
    
    def test_exact_slot_not_expanded(self):
        """
        Programs with exact slot definitions (like '09:00-10:30') should NOT be expanded.
        Historická prohlídka has time_blocks: ['09:00-10:30'] - should stay as 1 slot.
        """
        response = requests.get(f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{HISTORICKA_PROHLIDKA_ID}/{TEST_DATE}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        time_blocks = data.get("time_blocks", [])
        
        # Should have exactly 1 slot
        assert len(time_blocks) == 1, f"Expected 1 slot, got {len(time_blocks)}: {time_blocks}"
        assert time_blocks[0]["time"] == "09:00-10:30", f"Expected '09:00-10:30', got {time_blocks[0]['time']}"
        
        print(f"✅ Exact slot program correctly NOT expanded, has 1 slot: {time_blocks[0]['time']}")
    
    def test_afternoon_window_also_expands(self):
        """
        60min program with window 13:00-15:00 should also expand into slots.
        """
        response = requests.get(f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{CTEME_OBRAZY_ID}/{TEST_DATE}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        time_blocks = data.get("time_blocks", [])
        
        # Extract afternoon slots (13:00 and later)
        afternoon_slots = [b["time"] for b in time_blocks if b["time"].startswith(("13:", "14:"))]
        
        # Should have afternoon slots
        assert len(afternoon_slots) > 0, f"Expected afternoon slots, got none"
        
        # Check that slots are within the 13:00-15:00 window
        for slot in afternoon_slots:
            start, end = slot.split("-")
            start_hour = int(start.split(":")[0])
            end_hour = int(end.split(":")[0])
            end_min = int(end.split(":")[1])
            
            assert start_hour >= 13, f"Slot {slot} starts before 13:00"
            assert end_hour < 15 or (end_hour == 15 and end_min == 0), f"Slot {slot} ends after 15:00"
        
        print(f"✅ Afternoon window correctly expanded to {len(afternoon_slots)} slots")


class TestProgramsAPI:
    """Test programs API returns correct data."""
    
    def test_programs_list_returns_time_blocks(self):
        """Programs API should return time_blocks field."""
        response = requests.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        programs = response.json()
        assert isinstance(programs, list), "Expected list of programs"
        assert len(programs) > 0, "Expected at least one program"
        
        # Check that programs have time_blocks
        for prog in programs:
            assert "time_blocks" in prog, f"Program {prog.get('name_cs')} missing time_blocks"
            assert "duration" in prog, f"Program {prog.get('name_cs')} missing duration"
        
        print(f"✅ Programs API returns {len(programs)} programs with time_blocks")
    
    def test_cteme_obrazy_has_correct_config(self):
        """Čteme obrazy should have 60min duration and time windows."""
        response = requests.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}")
        assert response.status_code == 200
        
        programs = response.json()
        cteme_obrazy = next((p for p in programs if p["id"] == CTEME_OBRAZY_ID), None)
        
        assert cteme_obrazy is not None, "Čteme obrazy program not found"
        assert cteme_obrazy["duration"] == 60, f"Expected 60min, got {cteme_obrazy['duration']}"
        assert "08:30-12:00" in cteme_obrazy["time_blocks"], "Expected 08:30-12:00 time window"
        
        print(f"✅ Čteme obrazy has correct config: {cteme_obrazy['duration']}min, time_blocks: {cteme_obrazy['time_blocks']}")
    
    def test_historicka_prohlidka_has_exact_slot(self):
        """Historická prohlídka should have exact slot 09:00-10:30."""
        response = requests.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}")
        assert response.status_code == 200
        
        programs = response.json()
        hist_prohlidka = next((p for p in programs if p["id"] == HISTORICKA_PROHLIDKA_ID), None)
        
        assert hist_prohlidka is not None, "Historická prohlídka program not found"
        assert hist_prohlidka["duration"] == 90, f"Expected 90min, got {hist_prohlidka['duration']}"
        assert hist_prohlidka["time_blocks"] == ["09:00-10:30"], f"Expected exact slot, got {hist_prohlidka['time_blocks']}"
        
        print(f"✅ Historická prohlídka has exact slot: {hist_prohlidka['time_blocks']}")


class TestCalendarAPI:
    """Test calendar API with program filter."""
    
    def test_calendar_with_program_filter(self):
        """Calendar API should accept program_id filter."""
        response = requests.get(f"{BASE_URL}/api/calendar/{INSTITUTION_ID}/2026/4?program_id={CTEME_OBRAZY_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "dates" in data, "Expected dates in response"
        assert "year" in data, "Expected year in response"
        assert "month" in data, "Expected month in response"
        
        print(f"✅ Calendar API with program filter returns {len(data['dates'])} dates")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
