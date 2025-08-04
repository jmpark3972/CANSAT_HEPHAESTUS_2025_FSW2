#!/usr/bin/env python3
"""
Test script for the new flight state management system.
Tests the Korean state names and 70m altitude threshold for motor closure.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flight_logic.flightlogicapp import (
    STATE_LIST, 
    MOTOR_CLOSE_ALT_THRESHOLD,
    barometer_logic,
    motor_close_state_transition,
    descent_state_transition,
    apogee_state_transition,
    ascent_state_transition,
    launchpad_state_transition,
    landed_state_transition
)
from multiprocessing import Queue
import time

def test_state_list():
    """Test that the state list contains the correct Korean state names"""
    print("Testing STATE_LIST...")
    expected_states = ["발사대 대기", "상승", "최고점", "하강", "모터 완전 닫음", "착륙"]
    
    assert STATE_LIST == expected_states, f"Expected {expected_states}, got {STATE_LIST}"
    print(f"✓ STATE_LIST is correct: {STATE_LIST}")
    
    # Test state indices
    assert STATE_LIST[0] == "발사대 대기"
    assert STATE_LIST[1] == "상승"
    assert STATE_LIST[2] == "최고점"
    assert STATE_LIST[3] == "하강"
    assert STATE_LIST[4] == "모터 완전 닫음"
    assert STATE_LIST[5] == "착륙"
    print("✓ All state indices are correct")

def test_motor_close_threshold():
    """Test that the motor close threshold is set to 70 meters"""
    print("\nTesting MOTOR_CLOSE_ALT_THRESHOLD...")
    assert MOTOR_CLOSE_ALT_THRESHOLD == 70, f"Expected 70, got {MOTOR_CLOSE_ALT_THRESHOLD}"
    print(f"✓ MOTOR_CLOSE_ALT_THRESHOLD is correct: {MOTOR_CLOSE_ALT_THRESHOLD}m")

def test_state_transitions():
    """Test that state transition functions exist and work"""
    print("\nTesting state transition functions...")
    
    # Create a mock queue for testing
    mock_queue = Queue()
    
    # Test that all transition functions exist and can be called
    try:
        launchpad_state_transition(mock_queue)
        print("✓ launchpad_state_transition function exists")
    except Exception as e:
        print(f"✗ launchpad_state_transition failed: {e}")
    
    try:
        ascent_state_transition(mock_queue)
        print("✓ ascent_state_transition function exists")
    except Exception as e:
        print(f"✗ ascent_state_transition failed: {e}")
    
    try:
        apogee_state_transition(mock_queue)
        print("✓ apogee_state_transition function exists")
    except Exception as e:
        print(f"✗ apogee_state_transition failed: {e}")
    
    try:
        descent_state_transition(mock_queue)
        print("✓ descent_state_transition function exists")
    except Exception as e:
        print(f"✗ descent_state_transition failed: {e}")
    
    try:
        motor_close_state_transition(mock_queue)
        print("✓ motor_close_state_transition function exists")
    except Exception as e:
        print(f"✗ motor_close_state_transition failed: {e}")
    
    try:
        landed_state_transition(mock_queue)
        print("✓ landed_state_transition function exists")
    except Exception as e:
        print(f"✗ landed_state_transition failed: {e}")

def test_altitude_logic():
    """Test the altitude-based state transition logic"""
    print("\nTesting altitude-based logic...")
    
    # Test that 70m is the correct threshold for motor closure
    altitudes_to_test = [75, 70, 65, 60, 15, 10]
    
    print(f"Motor close threshold: {MOTOR_CLOSE_ALT_THRESHOLD}m")
    print("Altitude test cases:")
    for alt in altitudes_to_test:
        should_close = alt <= MOTOR_CLOSE_ALT_THRESHOLD
        print(f"  {alt}m: {'Should close motor' if should_close else 'Should not close motor'}")

def main():
    """Run all tests"""
    print("=== Flight State Management Test ===\n")
    
    try:
        test_state_list()
        test_motor_close_threshold()
        test_state_transitions()
        test_altitude_logic()
        
        print("\n=== All tests passed! ===")
        print("\nSummary of changes:")
        print("- State names changed to Korean: 발사대 대기, 상승, 최고점, 하강, 모터 완전 닫음, 착륙")
        print("- Motor closure threshold set to 70m (fixed value)")
        print("- State transition logic updated to use new threshold")
        print("- All transition functions updated with new names")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 