#!/usr/bin/env python3
"""
Integration tests for Goal Scheduling Flow
Tests the complete user journey from goal creation to calendar scheduling
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Service URLs
ORCHESTRATOR_URL = "http://localhost:8001"
CORE_URL = "http://localhost:8004"

# Test user
TEST_USER_ID = "test_flow_user"

def print_step(step_num: int, description: str):
    """Print test step with formatting"""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print('='*60)

def print_result(success: bool, message: str):
    """Print test result"""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")

def print_json(data: Dict[str, Any], title: str = "Response"):
    """Print JSON data nicely"""
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

# Test 1: Create Goal with Auto-generated Steps
def test_create_goal():
    print_step(1, "Create Goal - 'Выучить Python за 2 месяца'")

    response = requests.post(
        f"{ORCHESTRATOR_URL}/api/process",
        json={
            "user_id": TEST_USER_ID,
            "message": "Хочу выучить Python за 2 месяца. Я новичок, готов уделять 2 часа в день"
        }
    )

    result = response.json()
    print_json(result)

    # Verify goal was created
    assert result.get("success") == True, "Goal creation failed"
    assert "шаги" in result.get("text", "").lower() or "шаг" in result.get("text", "").lower(), "No steps mentioned"

    # Get goal from database
    goals_response = requests.get(
        f"{CORE_URL}/api/goals",
        params={"user_id": TEST_USER_ID, "status": "active"}
    )
    goals = goals_response.json()
    print_json(goals, "Created Goals")

    assert len(goals) > 0, "No goals found in database"
    goal = goals[0]
    assert len(goal["steps"]) > 0, "No steps generated"

    print_result(True, f"Goal created with {len(goal['steps'])} steps")
    return goal["id"]

# Test 2: Provide Deadline
def test_provide_deadline(goal_id: int):
    print_step(2, "Provide Deadline - 'Через 2 месяца'")

    response = requests.post(
        f"{ORCHESTRATOR_URL}/api/process",
        json={
            "user_id": TEST_USER_ID,
            "message": "Через 2 месяца"
        }
    )

    result = response.json()
    print_json(result)

    # Should offer scheduling
    assert result.get("success") == True, "Deadline processing failed"
    assert result.get("response_type") == "inline_buttons", "Should show inline buttons"
    assert result.get("buttons") is not None, "No buttons provided"

    buttons = result["buttons"]
    assert any("запланировать" in btn["text"].lower() for btn in buttons), "No scheduling button"

    print_result(True, "Deadline accepted, scheduling offered")
    return buttons

# Test 3: Accept Scheduling (Click 'Да, запланировать')
def test_accept_scheduling(goal_id: int):
    print_step(3, "Accept Scheduling - Click 'Да, запланировать'")

    response = requests.post(
        f"{ORCHESTRATOR_URL}/api/callback",
        json={
            "user_id": TEST_USER_ID,
            "callback_data": f"schedule_accept:{goal_id}"
        }
    )

    result = response.json()
    print_json(result)

    # Should show time preference buttons
    assert result.get("success") == True, "Scheduling acceptance failed"
    assert result.get("response_type") == "inline_buttons", "Should show time buttons"

    buttons = result["buttons"]
    assert any("утро" in btn["text"].lower() for btn in buttons), "No morning button"
    assert any("день" in btn["text"].lower() for btn in buttons), "No afternoon button"
    assert any("вечер" in btn["text"].lower() for btn in buttons), "No evening button"

    print_result(True, "Time preference buttons shown")
    return buttons

# Test 4: Select Time Preferences (Morning and Evening)
def test_select_time_preferences(goal_id: int):
    print_step(4, "Select Time Preferences - Morning and Evening")

    # Select morning
    response1 = requests.post(
        f"{ORCHESTRATOR_URL}/api/callback",
        json={
            "user_id": TEST_USER_ID,
            "callback_data": f"time_pref:morning:{goal_id}"
        }
    )
    result1 = response1.json()
    print_json(result1, "After selecting Morning")

    # Verify checkmark added
    buttons1 = result1.get("buttons", [])
    morning_btn = next((b for b in buttons1 if "morning" in b["callback"]), None)
    assert morning_btn and "✅" in morning_btn["text"], "No checkmark on morning button"

    # Select evening
    response2 = requests.post(
        f"{ORCHESTRATOR_URL}/api/callback",
        json={
            "user_id": TEST_USER_ID,
            "callback_data": f"time_pref:evening:{goal_id}"
        }
    )
    result2 = response2.json()
    print_json(result2, "After selecting Evening")

    # Verify both checkmarks
    buttons2 = result2.get("buttons", [])
    morning_btn2 = next((b for b in buttons2 if "morning" in b["callback"]), None)
    evening_btn2 = next((b for b in buttons2 if "evening" in b["callback"]), None)
    assert morning_btn2 and "✅" in morning_btn2["text"], "Morning checkmark lost"
    assert evening_btn2 and "✅" in evening_btn2["text"], "No checkmark on evening button"

    print_result(True, "Time preferences selected: Morning ✅, Evening ✅")
    return buttons2

# Test 5: Proceed to Day Selection
def test_proceed_to_days(goal_id: int):
    print_step(5, "Proceed to Day Selection - Click 'Далее'")

    response = requests.post(
        f"{ORCHESTRATOR_URL}/api/callback",
        json={
            "user_id": TEST_USER_ID,
            "callback_data": f"time_pref_done:{goal_id}"
        }
    )

    result = response.json()
    print_json(result)

    # Should show day preference buttons
    assert result.get("success") == True, "Day selection failed"
    assert result.get("response_type") == "inline_buttons", "Should show day buttons"

    buttons = result["buttons"]
    weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    for day in weekdays[:5]:  # Check at least weekdays exist
        assert any(day in btn["text"].lower() for btn in buttons), f"No {day} button"

    print_result(True, "Day selection buttons shown")
    return buttons

# Test 6: Select Day Preferences (Mon, Wed, Fri)
def test_select_day_preferences(goal_id: int):
    print_step(6, "Select Day Preferences - Mon, Wed, Fri")

    days = ["mon", "wed", "fri"]

    for day in days:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/callback",
            json={
                "user_id": TEST_USER_ID,
                "callback_data": f"day_pref:{day}:{goal_id}"
            }
        )
        result = response.json()
        print(f"Selected {day}")

    print_json(result, "After selecting Mon, Wed, Fri")

    # Verify checkmarks
    buttons = result.get("buttons", [])
    for day in days:
        day_btn = next((b for b in buttons if day in b["callback"]), None)
        assert day_btn and "✅" in day_btn["text"], f"No checkmark on {day}"

    print_result(True, "Day preferences selected: Mon ✅, Wed ✅, Fri ✅")
    return buttons

# Test 7: Generate Schedule
def test_generate_schedule(goal_id: int):
    print_step(7, "Generate Schedule - Click 'Далее'")

    response = requests.post(
        f"{ORCHESTRATOR_URL}/api/callback",
        json={
            "user_id": TEST_USER_ID,
            "callback_data": f"day_pref_done:{goal_id}"
        }
    )

    result = response.json()
    print_json(result)

    # Should show schedule preview
    assert result.get("success") == True, "Schedule generation failed"
    text = result.get("text", "")
    assert "расписание" in text.lower(), "No schedule in response"
    assert result.get("buttons") is not None, "No confirmation buttons"

    buttons = result["buttons"]
    assert any("добавить" in btn["text"].lower() for btn in buttons), "No confirm button"

    print_result(True, "Schedule generated and shown for confirmation")
    return buttons

# Test 8: Confirm Schedule
def test_confirm_schedule(goal_id: int):
    print_step(8, "Confirm Schedule - Click 'Да, добавить'")

    response = requests.post(
        f"{ORCHESTRATOR_URL}/api/callback",
        json={
            "user_id": TEST_USER_ID,
            "callback_data": f"schedule_confirm:{goal_id}"
        }
    )

    result = response.json()
    print_json(result)

    # Should create events
    assert result.get("success") == True, "Schedule confirmation failed"

    # Verify events were created in database
    events_response = requests.get(
        f"{CORE_URL}/api/events",
        params={
            "user_id": TEST_USER_ID,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        }
    )
    events = events_response.json()
    print_json(events, "Created Events")

    # Verify events have goal links
    goal_events = [e for e in events if e.get("linked_goal_id") == goal_id]
    assert len(goal_events) > 0, "No events linked to goal"

    # Verify event types
    for event in goal_events:
        assert event.get("event_type") == "goal_step", "Wrong event type"
        assert event.get("linked_goal_id") == goal_id, "Wrong goal link"

    print_result(True, f"Schedule confirmed! Created {len(goal_events)} events in calendar")
    return events

# Test 9: Verify Goal-Calendar Integration
def test_verify_integration(goal_id: int):
    print_step(9, "Verify Goal-Calendar Integration")

    # Get goal with steps
    goal_response = requests.get(
        f"{CORE_URL}/api/goals/{goal_id}",
        params={"user_id": TEST_USER_ID}
    )
    goal = goal_response.json()
    print_json(goal, "Goal with Steps")

    # Verify goal is marked as scheduled
    assert goal.get("is_scheduled") == True, "Goal not marked as scheduled"
    assert goal.get("target_deadline") is not None, "No deadline set"

    # Verify steps have planning info
    steps_with_dates = [s for s in goal["steps"] if s.get("planned_date")]
    assert len(steps_with_dates) > 0, "No steps have planned dates"

    print_result(True, f"Integration verified: {len(steps_with_dates)} steps scheduled")

    # Print summary
    print("\n" + "="*60)
    print("INTEGRATION SUMMARY")
    print("="*60)
    print(f"Goal ID: {goal_id}")
    print(f"Goal Title: {goal['title']}")
    print(f"Total Steps: {len(goal['steps'])}")
    print(f"Scheduled Steps: {len(steps_with_dates)}")
    print(f"Is Scheduled: {goal['is_scheduled']}")
    print(f"Deadline: {goal.get('target_deadline', 'N/A')}")
    print("="*60)

# Main test runner
def run_all_tests():
    """Run complete flow test"""
    print("\n" + "="*60)
    print("GOAL SCHEDULING FLOW - INTEGRATION TESTS")
    print("="*60)

    try:
        # Run flow
        goal_id = test_create_goal()
        buttons = test_provide_deadline(goal_id)
        buttons = test_accept_scheduling(goal_id)
        buttons = test_select_time_preferences(goal_id)
        buttons = test_proceed_to_days(goal_id)
        buttons = test_select_day_preferences(goal_id)
        buttons = test_generate_schedule(goal_id)
        events = test_confirm_schedule(goal_id)
        test_verify_integration(goal_id)

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        return True

    except AssertionError as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        return False
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ ERROR: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
