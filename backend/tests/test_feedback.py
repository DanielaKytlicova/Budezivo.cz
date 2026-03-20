"""
Test suite for Teacher Feedback System APIs.

Tests:
- Feedback Questions CRUD (Admin only)
- Feedback Submissions listing with filters
- Feedback Statistics
- CSV Export
- Role-based access control
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


class TestFeedbackQuestions:
    """Test feedback questions CRUD operations (Admin only)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get('token')
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.created_question_ids = []
        yield
        # Cleanup: deactivate created questions
        for qid in self.created_question_ids:
            try:
                requests.delete(f"{BASE_URL}/api/feedback/questions/{qid}", headers=self.headers)
            except:
                pass
    
    def test_get_questions_list(self):
        """GET /api/feedback/questions - List active questions"""
        response = requests.get(f"{BASE_URL}/api/feedback/questions", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} active questions")
    
    def test_get_questions_include_inactive(self):
        """GET /api/feedback/questions?include_inactive=true - List all questions"""
        response = requests.get(
            f"{BASE_URL}/api/feedback/questions?include_inactive=true", 
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} total questions (including inactive)")
    
    def test_create_question_rating_type(self):
        """POST /api/feedback/questions - Create rating type question"""
        payload = {
            "question_text": f"TEST_Rating_Question_{uuid.uuid4().hex[:8]}",
            "question_type": "rating",
            "is_required": True,
            "display_order": 99
        }
        response = requests.post(
            f"{BASE_URL}/api/feedback/questions", 
            json=payload, 
            headers=self.headers
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should contain id"
        assert data["question_text"] == payload["question_text"]
        assert data["question_type"] == "rating"
        assert data["is_required"] == True
        assert data["is_active"] == True
        
        self.created_question_ids.append(data["id"])
        print(f"Created rating question: {data['id']}")
    
    def test_create_question_yesno_type(self):
        """POST /api/feedback/questions - Create yes/no type question"""
        payload = {
            "question_text": f"TEST_YesNo_Question_{uuid.uuid4().hex[:8]}",
            "question_type": "yesno",
            "is_required": False,
            "display_order": 98
        }
        response = requests.post(
            f"{BASE_URL}/api/feedback/questions", 
            json=payload, 
            headers=self.headers
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        
        assert data["question_type"] == "yesno"
        assert data["is_required"] == False
        
        self.created_question_ids.append(data["id"])
        print(f"Created yesno question: {data['id']}")
    
    def test_create_question_text_type(self):
        """POST /api/feedback/questions - Create text type question"""
        payload = {
            "question_text": f"TEST_Text_Question_{uuid.uuid4().hex[:8]}",
            "question_type": "text",
            "is_required": True,
            "display_order": 97
        }
        response = requests.post(
            f"{BASE_URL}/api/feedback/questions", 
            json=payload, 
            headers=self.headers
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        
        assert data["question_type"] == "text"
        
        self.created_question_ids.append(data["id"])
        print(f"Created text question: {data['id']}")
    
    def test_update_question(self):
        """PUT /api/feedback/questions/{id} - Update question"""
        # First create a question
        create_payload = {
            "question_text": f"TEST_Update_Question_{uuid.uuid4().hex[:8]}",
            "question_type": "rating",
            "is_required": True,
            "display_order": 96
        }
        create_response = requests.post(
            f"{BASE_URL}/api/feedback/questions", 
            json=create_payload, 
            headers=self.headers
        )
        assert create_response.status_code == 201
        question_id = create_response.json()["id"]
        self.created_question_ids.append(question_id)
        
        # Update the question
        update_payload = {
            "question_text": "Updated Question Text",
            "is_required": False,
            "display_order": 50
        }
        update_response = requests.put(
            f"{BASE_URL}/api/feedback/questions/{question_id}",
            json=update_payload,
            headers=self.headers
        )
        assert update_response.status_code == 200, f"Failed: {update_response.text}"
        data = update_response.json()
        
        assert data["question_text"] == "Updated Question Text"
        assert data["is_required"] == False
        assert data["display_order"] == 50
        print(f"Updated question: {question_id}")
    
    def test_delete_question_soft_delete(self):
        """DELETE /api/feedback/questions/{id} - Soft delete (deactivate)"""
        # First create a question
        create_payload = {
            "question_text": f"TEST_Delete_Question_{uuid.uuid4().hex[:8]}",
            "question_type": "rating",
            "is_required": True,
            "display_order": 95
        }
        create_response = requests.post(
            f"{BASE_URL}/api/feedback/questions", 
            json=create_payload, 
            headers=self.headers
        )
        assert create_response.status_code == 201
        question_id = create_response.json()["id"]
        
        # Delete (deactivate) the question
        delete_response = requests.delete(
            f"{BASE_URL}/api/feedback/questions/{question_id}",
            headers=self.headers
        )
        assert delete_response.status_code == 200, f"Failed: {delete_response.text}"
        
        # Verify it's deactivated by checking include_inactive
        list_response = requests.get(
            f"{BASE_URL}/api/feedback/questions?include_inactive=true",
            headers=self.headers
        )
        questions = list_response.json()
        deactivated = next((q for q in questions if q["id"] == question_id), None)
        assert deactivated is not None, "Question should still exist"
        assert deactivated["is_active"] == False, "Question should be deactivated"
        print(f"Soft deleted question: {question_id}")
    
    def test_update_nonexistent_question(self):
        """PUT /api/feedback/questions/{id} - 404 for non-existent question"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/feedback/questions/{fake_id}",
            json={"question_text": "Test"},
            headers=self.headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for non-existent question")


class TestFeedbackSubmissions:
    """Test feedback submissions listing with filters"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get('token')
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_submissions_list(self):
        """GET /api/feedback/submissions - List all submissions"""
        response = requests.get(f"{BASE_URL}/api/feedback/submissions", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} feedback submissions")
    
    def test_get_submissions_with_status_filter(self):
        """GET /api/feedback/submissions?status_filter=submitted"""
        response = requests.get(
            f"{BASE_URL}/api/feedback/submissions?status_filter=submitted",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # All returned items should have status=submitted
        for item in data:
            assert item.get("status") == "submitted", f"Expected submitted status, got {item.get('status')}"
        print(f"Found {len(data)} submitted feedbacks")
    
    def test_get_submissions_with_pending_filter(self):
        """GET /api/feedback/submissions?status_filter=pending"""
        response = requests.get(
            f"{BASE_URL}/api/feedback/submissions?status_filter=pending",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        for item in data:
            assert item.get("status") == "pending", f"Expected pending status, got {item.get('status')}"
        print(f"Found {len(data)} pending feedbacks")
    
    def test_get_submissions_with_rating_filter(self):
        """GET /api/feedback/submissions?min_rating=4"""
        response = requests.get(
            f"{BASE_URL}/api/feedback/submissions?min_rating=4",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        for item in data:
            if item.get("overall_rating"):
                assert item["overall_rating"] >= 4, f"Rating should be >= 4"
        print(f"Found {len(data)} feedbacks with rating >= 4")
    
    def test_get_submissions_with_pagination(self):
        """GET /api/feedback/submissions?limit=5&offset=0"""
        response = requests.get(
            f"{BASE_URL}/api/feedback/submissions?limit=5&offset=0",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert len(data) <= 5, "Should return at most 5 items"
        print(f"Pagination working: returned {len(data)} items")
    
    def test_submissions_response_structure(self):
        """Verify submission response has required fields"""
        response = requests.get(f"{BASE_URL}/api/feedback/submissions", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            item = data[0]
            required_fields = ["id", "reservation_id", "status", "created_at"]
            for field in required_fields:
                assert field in item, f"Missing required field: {field}"
            print(f"Response structure verified with fields: {list(item.keys())}")
        else:
            print("No submissions to verify structure")


class TestFeedbackStatistics:
    """Test feedback statistics endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get('token')
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_statistics(self):
        """GET /api/feedback/statistics - Get feedback statistics"""
        response = requests.get(f"{BASE_URL}/api/feedback/statistics", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_feedbacks" in data, "Missing total_feedbacks"
        assert "average_rating" in data, "Missing average_rating"
        assert "recommendation_rate" in data, "Missing recommendation_rate"
        assert "by_rating" in data, "Missing by_rating"
        assert "by_program" in data, "Missing by_program"
        
        # Verify by_rating structure
        assert isinstance(data["by_rating"], dict), "by_rating should be a dict"
        
        print(f"Statistics: total={data['total_feedbacks']}, avg_rating={data['average_rating']}, rec_rate={data['recommendation_rate']}")
    
    def test_statistics_by_rating_distribution(self):
        """Verify by_rating contains 1-5 keys"""
        response = requests.get(f"{BASE_URL}/api/feedback/statistics", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        by_rating = data.get("by_rating", {})
        for rating in [1, 2, 3, 4, 5]:
            assert rating in by_rating or str(rating) in by_rating, f"Missing rating {rating} in distribution"
        print(f"Rating distribution: {by_rating}")
    
    def test_statistics_by_program(self):
        """Verify by_program structure"""
        response = requests.get(f"{BASE_URL}/api/feedback/statistics", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        by_program = data.get("by_program", [])
        assert isinstance(by_program, list), "by_program should be a list"
        
        if len(by_program) > 0:
            item = by_program[0]
            assert "program_name" in item, "Missing program_name"
            assert "count" in item, "Missing count"
            print(f"Programs with feedback: {[p['program_name'] for p in by_program]}")
        else:
            print("No program statistics available")


class TestFeedbackExport:
    """Test feedback CSV export"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get('token')
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_export_csv(self):
        """GET /api/feedback/export - Export feedback as CSV"""
        response = requests.get(f"{BASE_URL}/api/feedback/export", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify content type
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected CSV content type, got {content_type}"
        
        # Verify content disposition
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, "Should be attachment"
        assert "feedback_export" in content_disp, "Filename should contain feedback_export"
        
        print(f"CSV export successful, size: {len(response.content)} bytes")
    
    def test_export_csv_with_date_filter(self):
        """GET /api/feedback/export?date_from=2025-01-01&date_to=2026-12-31"""
        response = requests.get(
            f"{BASE_URL}/api/feedback/export?date_from=2025-01-01&date_to=2026-12-31",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print("CSV export with date filter successful")


class TestFeedbackAuth:
    """Test authentication requirements for feedback endpoints"""
    
    def test_questions_requires_auth(self):
        """GET /api/feedback/questions - Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/feedback/questions")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Questions endpoint correctly requires auth")
    
    def test_submissions_requires_auth(self):
        """GET /api/feedback/submissions - Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/feedback/submissions")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Submissions endpoint correctly requires auth")
    
    def test_statistics_requires_auth(self):
        """GET /api/feedback/statistics - Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/feedback/statistics")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Statistics endpoint correctly requires auth")
    
    def test_export_requires_auth(self):
        """GET /api/feedback/export - Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/feedback/export")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Export endpoint correctly requires auth")
    
    def test_create_question_requires_auth(self):
        """POST /api/feedback/questions - Should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/feedback/questions",
            json={"question_text": "Test", "question_type": "rating"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Create question endpoint correctly requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
