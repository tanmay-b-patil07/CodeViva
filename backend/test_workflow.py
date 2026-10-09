#!/usr/bin/env python3
"""Comprehensive testing for CodeViva student and teacher workflows."""

import asyncio
import httpx
import json
import sys
from datetime import datetime

API_BASE = "http://localhost:8000/api"

class CodeVivaTest:
    def __init__(self):
        self.results = []
        self.client = None
        self.student_token = None
        self.teacher_token = None
        self.practice_session_id = None
        self.question_id = None

    async def setup(self):
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(timeout=30.0)

    async def cleanup(self):
        """Clean up HTTP client."""
        if self.client:
            await self.client.aclose()

    def log_result(self, test_name, status, details=""):
        """Log test result."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        result = {
            "test": test_name,
            "status": status,
            "time": timestamp,
            "details": details
        }
        self.results.append(result)
        mark = "OK" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
        print(f"  [{mark}] {test_name}")
        if details:
            print(f"      {details}")

    async def test_student_registration(self):
        """Test student registration."""
        print("\n1. STUDENT REGISTRATION")
        try:
            response = await self.client.post(
                f"{API_BASE}/auth/register",
                json={
                    "email": "newstudent@codeviva.local",
                    "password": "TestPassword123!",
                    "full_name": "New Student"
                }
            )
            if response.status_code in [200, 201]:
                self.log_result("Student Registration", "PASS", f"Status: {response.status_code}")
                return True
            else:
                self.log_result("Student Registration", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Student Registration", "FAIL", f"Error: {e}")
            return False

    async def test_student_login(self):
        """Test student login."""
        print("\n2. STUDENT LOGIN")
        try:
            response = await self.client.post(
                f"{API_BASE}/auth/login",
                json={
                    "email": "student1.demo@codeviva.local",
                    "password": "CodeViva-Demo-2026!"
                }
            )
            if response.status_code == 200:
                data = response.json()
                # Token is in cookies, not response body
                if self.client.cookies:
                    self.student_token = self.client.cookies.get("Authorization")
                    if not self.student_token:
                        # Try to extract from Set-Cookie header or use the client's cookies
                        self.student_token = "cookie_based"
                    self.log_result("Student Login", "PASS", f"Email: {data.get('email')}")
                    return True
            self.log_result("Student Login", "FAIL", f"Status: {response.status_code}, Response: {response.text[:100]}")
            return False
        except Exception as e:
            self.log_result("Student Login", "FAIL", f"Error: {e}")
            return False

    async def test_teacher_registration(self):
        """Test teacher registration."""
        print("\n3. TEACHER REGISTRATION")
        try:
            response = await self.client.post(
                f"{API_BASE}/auth/register-teacher",
                json={
                    "email": "newteacher@codeviva.local",
                    "password": "TeacherPass123!",
                    "full_name": "New Teacher",
                    "invite_code": "TEACHER_CODE"
                }
            )
            if response.status_code in [200, 201]:
                self.log_result("Teacher Registration", "PASS", f"Status: {response.status_code}")
                return True
            else:
                self.log_result("Teacher Registration", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Teacher Registration", "FAIL", f"Error: {e}")
            return False

    async def test_teacher_login(self):
        """Test teacher login."""
        print("\n4. TEACHER LOGIN")
        try:
            response = await self.client.post(
                f"{API_BASE}/auth/login",
                json={
                    "email": "teacher.demo@codeviva.local",
                    "password": "CodeViva-Demo-2026!"
                }
            )
            if response.status_code == 200:
                data = response.json()
                # Token is in cookies
                if self.client.cookies:
                    self.teacher_token = "cookie_based"
                    self.log_result("Teacher Login", "PASS", f"Email: {data.get('email')}")
                    return True
            self.log_result("Teacher Login", "FAIL", f"Status: {response.status_code}, Response: {response.text[:100]}")
            return False
        except Exception as e:
            self.log_result("Teacher Login", "FAIL", f"Error: {e}")
            return False

    async def test_student_profile(self):
        """Test getting student profile."""
        print("\n5. GET STUDENT PROFILE")
        if not self.student_token:
            self.log_result("Get Student Profile", "SKIP", "No token")
            return False

        try:
            # With cookie-based auth, no need for Bearer header
            response = await self.client.get(
                f"{API_BASE}/auth/me"
            )
            if response.status_code == 200:
                data = response.json()
                self.log_result("Get Student Profile", "PASS", f"Email: {data.get('email')}")
                return True
            else:
                self.log_result("Get Student Profile", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get Student Profile", "FAIL", f"Error: {e}")
            return False

    async def test_list_practice_sessions(self):
        """Test listing practice sessions."""
        print("\n6. LIST PRACTICE SESSIONS")
        if not self.student_token:
            self.log_result("List Practice Sessions", "SKIP", "No token")
            return False

        try:
            response = await self.client.get(
                f"{API_BASE}/student/practice"
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                self.log_result("List Practice Sessions", "PASS", f"Sessions: {count}")
                return True
            else:
                self.log_result("List Practice Sessions", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("List Practice Sessions", "FAIL", f"Error: {e}")
            return False

    async def test_practice_question_generation(self):
        """Test generating practice questions from Python code."""
        print("\n7. PRACTICE QUESTION GENERATION")
        if not self.student_token:
            self.log_result("Generate Practice Question", "SKIP", "No token")
            return False

        # Sample Python code for testing
        sample_code = """def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)
"""

        try:
            response = await self.client.post(
                f"{API_BASE}/student/practice",
                json={"code": sample_code, "language": "python"}
            )
            if response.status_code == 200:
                data = response.json()
                self.practice_session_id = data.get("id")
                self.log_result("Generate Practice Question", "PASS", f"Session ID: {self.practice_session_id}")
                return True
            else:
                self.log_result("Generate Practice Question", "FAIL", f"Status: {response.status_code}")
                if response.status_code != 200:
                    print(f"      Response: {response.text[:200]}")
                return False
        except Exception as e:
            self.log_result("Generate Practice Question", "FAIL", f"Error: {e}")
            return False

    async def test_stream_questions(self):
        """Test streaming practice questions."""
        print("\n8. STREAM PRACTICE QUESTIONS")
        if not self.student_token or not self.practice_session_id:
            self.log_result("Stream Questions", "SKIP", "No session")
            return False

        try:
            response = await self.client.get(
                f"{API_BASE}/student/practice/{self.practice_session_id}/stream"
            )
            if response.status_code == 200:
                # SSE stream would come here
                self.log_result("Stream Questions", "PASS", "Stream endpoint responding")
                return True
            else:
                self.log_result("Stream Questions", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Stream Questions", "FAIL", f"Error: {e}")
            return False

    async def test_submit_answer(self):
        """Test submitting an answer to a practice question."""
        print("\n9. SUBMIT ANSWER")
        if not self.student_token or not self.practice_session_id:
            self.log_result("Submit Answer", "SKIP", "No session")
            return False

        try:
            response = await self.client.post(
                f"{API_BASE}/student/submissions",
                json={
                    "practice_session_id": self.practice_session_id,
                    "question_id": "question_1",
                    "answer": "The function recursively calculates Fibonacci numbers",
                    "code": "fibonacci(5)"
                }
            )
            if response.status_code in [200, 201]:
                self.log_result("Submit Answer", "PASS", f"Status: {response.status_code}")
                return True
            else:
                self.log_result("Submit Answer", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Submit Answer", "FAIL", f"Error: {e}")
            return False

    async def test_evaluation_metrics(self):
        """Test getting evaluation metrics."""
        print("\n10. EVALUATION METRICS")
        if not self.student_token:
            self.log_result("Get Evaluation Metrics", "SKIP", "No token")
            return False

        try:
            response = await self.client.get(
                f"{API_BASE}/student/submissions"
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                self.log_result("Get Evaluation Metrics", "PASS", f"Submissions: {count}")
                return True
            else:
                self.log_result("Get Evaluation Metrics", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get Evaluation Metrics", "FAIL", f"Error: {e}")
            return False

    async def test_teacher_groups(self):
        """Test teacher managing groups."""
        print("\n11. TEACHER GROUPS")
        if not self.teacher_token:
            self.log_result("List Teacher Groups", "SKIP", "No token")
            return False

        try:
            response = await self.client.get(
                f"{API_BASE}/teacher/groups"
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                self.log_result("List Teacher Groups", "PASS", f"Groups: {count}")
                return True
            else:
                self.log_result("List Teacher Groups", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("List Teacher Groups", "FAIL", f"Error: {e}")
            return False

    async def run_all_tests(self):
        """Run all tests."""
        print("=" * 70)
        print("CODEVIVA COMPREHENSIVE WORKFLOW TESTING")
        print("=" * 70)

        await self.setup()

        try:
            # Authentication Tests
            print("\n[PHASE 1: AUTHENTICATION]")
            await self.test_student_registration()
            await self.test_student_login()
            await self.test_teacher_registration()
            await self.test_teacher_login()

            # Student Profile Tests
            print("\n[PHASE 2: STUDENT PROFILE]")
            await self.test_student_profile()
            await self.test_list_practice_sessions()

            # Practice Workflow Tests
            print("\n[PHASE 3: PRACTICE WORKFLOW]")
            await self.test_practice_question_generation()
            await self.test_stream_questions()
            await self.test_submit_answer()
            await self.test_evaluation_metrics()

            # Teacher Tests
            print("\n[PHASE 4: TEACHER MANAGEMENT]")
            await self.test_teacher_groups()

        finally:
            await self.cleanup()

        # Print Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        total = len(self.results)

        print(f"\nResults:")
        print(f"  PASSED:  {passed}/{total}")
        print(f"  FAILED:  {failed}/{total}")
        print(f"  SKIPPED: {skipped}/{total}")
        print(f"\nSuccess Rate: {passed}/{total-skipped} = {100*passed/(total-skipped) if total > skipped else 0:.1f}%")

        print(f"\nDetailed Results:")
        for result in self.results:
            status_mark = "OK" if result["status"] == "PASS" else "FAIL" if result["status"] == "FAIL" else "SKIP"
            print(f"  [{status_mark}] {result['test']:<35} [{result['status']}]")
            if result["details"]:
                print(f"      -> {result['details']}")

        print("\n" + "=" * 70)

async def main():
    """Main entry point."""
    tester = CodeVivaTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
