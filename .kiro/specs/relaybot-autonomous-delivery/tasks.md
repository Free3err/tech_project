# Implementation Plan: RelayBot Autonomous Delivery System

## Overview

This implementation plan breaks down the RelayBot autonomous delivery robot into incremental coding tasks. The approach follows a phased development strategy: core infrastructure → navigation system → sensor integration → state machine logic → hardware control → error handling. Each task builds on previous work, with property-based tests integrated throughout to validate correctness early.

The implementation extends existing code (qrScanner.py, serialConnection.py, db modules, ideal_program.ino) with minimal modifications, adding new autonomous capabilities through modular components.

## Tasks

- [x] 1. Set up project infrastructure and configuration
  - Create config.py with all system parameters (coordinates, tolerances, hardware settings)
  - Create requirements.txt with new dependencies (hypothesis, numpy, scipy, pyyaml)
  - Set up test directory structure (tests/unit/, tests/property/, tests/integration/)
  - Create conftest.py with pytest fixtures and test database setup
  - _Requirements: 14.1_

- [x] 2. Implement serial communication extensions
  - [x] 2.1 Extend serialConnection.py with new command functions
    - Add send_motor_command(left_speed, right_speed, left_dir, right_dir)
    - Add send_servo_command(angle)
    - Add send_led_command(command)
    - Add read_sensor_data() for receiving Arduino data
    - Maintain backward compatibility with existing code
    - _Requirements: 12.1, 12.2, 12.3_
  
  - [ ]* 2.2 Write unit tests for serial communication
    - Test command formatting and sending
    - Test sensor data parsing
    - Mock serial port for testing
    - _Requirements: 12.1_
  
  - [ ]* 2.3 Write property test for serial command reliability
    - **Property 18: Serial Command Reliability**
    - **Validates: Requirements 12.5**

- [x] 3. Implement data models and position tracking
  - [x] 3.1 Create data structures in navigation.py
    - Implement Position dataclass (x, y, theta)
    - Implement ScanPoint dataclass (distance, angle, intensity)
    - Implement Waypoint dataclass (x, y, tolerance)
    - Implement StateContext dataclass for state machine
    - _Requirements: 9.1_
  
  - [ ]* 3.2 Write unit tests for data structures
    - Test dataclass initialization and field access
    - Test coordinate transformations
    - _Requirements: 9.1_

- [x] 4. Implement odometry system
  - [x] 4.1 Create odometry.py with OdometrySystem class
    - Implement __init__ with wheel_base and wheel_radius parameters
    - Implement update(left_ticks, right_ticks, dt) for position calculation
    - Implement get_pose() returning (x, y, theta)
    - Implement reset(x, y, theta) for position initialization
    - Use differential drive kinematics for position updates
    - _Requirements: 11.5, 9.4_
  
  - [ ]* 4.2 Write property test for odometry position delta
    - **Property 16: Odometry Position Delta**
    - **Validates: Requirements 11.5**
  
  - [ ]* 4.3 Write unit tests for odometry edge cases
    - Test zero movement (no ticks)
    - Test pure rotation (opposite wheel directions)
    - Test straight line movement (equal ticks)
    - _Requirements: 11.5_

- [x] 5. Implement LiDAR interface
  - [x] 5.1 Create lidar_interface.py with LiDARInterface class
    - Implement __init__ with serial port configuration for LDROBOT D500
    - Implement get_scan() returning list of ScanPoint objects
    - Implement detect_person() using clustering algorithm for person detection
    - Implement get_obstacles(min_distance) for obstacle detection
    - Add noise filtering for reliable detection within 5 meters
    - _Requirements: 11.1, 11.2, 11.3_
  
  - [ ]* 5.2 Write property test for LiDAR update rate
    - **Property 14: LiDAR Update Rate**
    - **Validates: Requirements 11.1**
  
  - [ ]* 5.3 Write property test for person position reporting
    - **Property 25: Person Position Reporting**
    - **Validates: Requirements 11.2**
  
  - [ ]* 5.4 Write unit tests for LiDAR processing
    - Test person detection with known scan patterns
    - Test obstacle detection at various distances
    - Test noise filtering
    - _Requirements: 11.2, 11.3_

- [x] 6. Checkpoint - Ensure sensor tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement navigation system core
  - [x] 7.1 Create navigation.py with NavigationSystem class
    - Implement __init__ with map file, LiDAR, odometry, and serial communication
    - Load environment map from YAML file
    - Initialize particle filter for localization (100-500 particles)
    - Implement get_current_position() returning (x, y, theta)
    - Implement stop() for emergency stop
    - _Requirements: 9.1, 9.6_
  
  - [x] 7.2 Implement localization update
    - Implement update_localization() using particle filter
    - Integrate LiDAR scan matching with known map
    - Integrate odometry for motion prediction
    - Resample particles based on likelihood
    - _Requirements: 9.6, 9.4, 9.7_
  
  - [ ]* 7.3 Write property test for localization update rate
    - **Property 15: Localization Update Rate**
    - **Validates: Requirements 9.7**
  
  - [ ]* 7.4 Write property test for coordinate system consistency
    - **Property 24: Coordinate System Consistency**
    - **Validates: Requirements 9.1**

- [x] 8. Implement path planning
  - [x] 8.1 Implement A* path planning algorithm
    - Implement plan_path(start, goal) using A* on occupancy grid
    - Generate waypoint list from start to goal
    - Handle unreachable goals gracefully
    - _Requirements: 9.3_
  
  - [x] 8.2 Implement obstacle avoidance
    - Integrate dynamic obstacles from LiDAR into path planning
    - Maintain 30cm clearance from obstacles
    - Replan path when new obstacles detected
    - _Requirements: 4.3, 6.3_
  
  - [ ]* 8.3 Write property test for path planning completeness
    - **Property 8: Path Planning Completeness**
    - **Validates: Requirements 4.1, 6.1, 8.1, 9.3**
  
  - [ ]* 8.4 Write property test for obstacle avoidance
    - **Property 10: Obstacle Avoidance**
    - **Validates: Requirements 4.3, 6.3**
  
  - [ ]* 8.5 Write unit tests for path planning edge cases
    - Test path to current position (zero distance)
    - Test path with completely blocked environment
    - Test path around obstacles
    - _Requirements: 9.3_

- [x] 9. Implement navigation control
  - [x] 9.1 Implement navigate_to(target_x, target_y) method
    - Plan path to target using plan_path()
    - Follow waypoints using PID controller for smooth movement
    - Send motor commands via serial communication
    - Monitor position and replan if deviation exceeds threshold
    - Return True when goal reached within tolerance, False on error
    - _Requirements: 4.1, 4.2, 4.4_
  
  - [ ]* 9.2 Write property test for navigation accuracy
    - **Property 9: Navigation Accuracy**
    - **Validates: Requirements 1.4, 4.4, 6.4, 9.2**
  
  - [ ]* 9.3 Write unit tests for navigation control
    - Test PID controller behavior
    - Test waypoint following
    - Test goal reached detection
    - _Requirements: 4.4_

- [x] 10. Checkpoint - Ensure navigation tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement audio system
  - [x] 11.1 Create audio_system.py with AudioSystem class
    - Implement __init__ with audio directory path
    - Implement play(audio_file, blocking) using playsound3
    - Implement request_qr_code() playing request_qr.wav
    - Implement announce_order_accepted() playing order_accepted.wav
    - Implement announce_order_rejected() playing order_rejected.wav
    - Implement announce_order_number(order_id) playing order-specific audio
    - Implement greet_delivery() playing delivery_greeting.wav
    - Implement stop() for stopping playback
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_
  
  - [ ]* 11.2 Write property test for audio-state mapping
    - **Property 23: Audio-State Mapping**
    - **Validates: Requirements 3.1, 5.1, 7.1, 13.1, 13.4, 13.5**
  
  - [ ]* 11.3 Write unit tests for audio system
    - Test audio file loading
    - Test playback (mock playsound3)
    - Test missing audio file handling
    - _Requirements: 13.1_

- [x] 12. Implement box mechanism controller
  - [x] 12.1 Create box_controller.py with BoxController class
    - Implement __init__ with serial communication reference
    - Implement open() sending servo command for 90 degrees
    - Implement close() sending servo command for 0 degrees
    - Implement is_open() tracking current box state
    - Add smooth movement with gradual angle changes
    - _Requirements: 15.1, 15.2, 15.3, 15.4_
  
  - [ ]* 12.2 Write property test for box opening control
    - **Property 20: Box Opening Control**
    - **Validates: Requirements 15.1, 15.3**
  
  - [ ]* 12.3 Write property test for box closing control
    - **Property 21: Box Closing Control**
    - **Validates: Requirements 7.4, 15.2, 15.4**
  
  - [x]* 12.4 Write unit tests for box controller
    - Test open/close commands
    - Test state tracking
    - Test servo failure handling
    - _Requirements: 15.6_

- [x] 13. Extend order verification system
  - [x] 13.1 Modify qrScanner.py for state machine integration
    - Add OrderVerificationSystem class wrapping existing qr_scanner()
    - Implement start_scanning(callback) for non-blocking operation
    - Implement stop_scanning() to stop camera
    - Implement verify_order(order_data) using existing check_order()
    - Add callback mechanism to notify state machine of scan results
    - Maintain existing functionality for standalone use
    - _Requirements: 3.2, 3.3, 3.4_
  
  - [ ]* 13.2 Write property test for QR code parsing
    - **Property 5: QR Code Parsing**
    - **Validates: Requirements 3.3**
  
  - [ ]* 13.3 Write property test for order validation round trip
    - **Property 6: Order Validation Round Trip**
    - **Validates: Requirements 3.4, 3.5**
  
  - [ ]* 13.4 Write property test for invalid order rejection
    - **Property 7: Invalid Order Rejection**
    - **Validates: Requirements 3.6**
  
  - [ ]* 13.5 Write unit tests for order verification
    - Test QR code detection and decoding
    - Test database query with test data
    - Test malformed JSON handling
    - _Requirements: 3.2, 3.3, 3.4_

- [x] 14. Checkpoint - Ensure subsystem tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Implement state machine core
  - [x] 15.1 Create state_machine.py with State enum and StateMachine class
    - Define State enum: WAITING, APPROACHING, VERIFYING, NAVIGATING_TO_WAREHOUSE, LOADING, RETURNING_TO_CUSTOMER, DELIVERING, RESETTING, ERROR_RECOVERY
    - Implement __init__ with references to all subsystems (navigation, audio, order_verifier, serial_comm, lidar, box_controller)
    - Implement transition_to(new_state) with logging
    - Implement handle_error(error) for error handling
    - Initialize StateContext for tracking positions and order info
    - _Requirements: 10.1, 10.2_
  
  - [ ]* 15.2 Write property test for state transition logging
    - **Property 12: State Transition Logging**
    - **Validates: Requirements 10.2**
  
  - [ ]* 15.3 Write unit tests for state machine initialization
    - Test state enum values
    - Test initial state is WAITING
    - Test subsystem references
    - _Requirements: 10.1_

- [x] 16. Implement WAITING state behavior
  - [x] 16.1 Implement update_waiting_state() method
    - Monitor LiDAR for person detection in delivery zone
    - Send idle LED animation command
    - Maintain position at home (0,0)
    - Transition to APPROACHING when person detected
    - _Requirements: 1.2, 1.3, 2.2_
  
  - [ ]* 16.2 Write property test for person detection triggers approach
    - **Property 2: Person Detection Triggers Approach**
    - **Validates: Requirements 2.2**
  
  - [ ]* 16.3 Write property test for state-LED mapping (WAITING)
    - **Property 19: State-LED Mapping** (partial)
    - **Validates: Requirements 1.3, 12.3**

- [x] 17. Implement APPROACHING state behavior
  - [x] 17.1 Implement update_approaching_state() method
    - Continuously track customer position with LiDAR
    - Navigate toward customer using navigate_to()
    - Check distance to customer, transition to VERIFYING when < 50cm
    - If customer disappears, stop and transition to WAITING
    - Send moving LED animation command
    - _Requirements: 2.3, 2.4, 2.5, 2.6_
  
  - [ ]* 17.2 Write property test for customer disappearance stops approach
    - **Property 3: Customer Disappearance Stops Approach**
    - **Validates: Requirements 2.5**
  
  - [ ]* 17.3 Write property test for proximity triggers verification
    - **Property 4: Proximity Triggers Verification**
    - **Validates: Requirements 2.6**

- [x] 18. Implement VERIFYING state behavior
  - [x] 18.1 Implement update_verifying_state() method
    - Play QR code request audio
    - Start QR scanning with callback
    - Handle scan timeout (30 seconds)
    - On valid order: store order_id, store customer position, transition to NAVIGATING_TO_WAREHOUSE
    - On invalid order: play rejection audio, transition to WAITING
    - Send waiting LED animation command
    - _Requirements: 3.1, 3.5, 3.6, 5.5_
  
  - [ ]* 18.2 Write property test for customer position persistence
    - **Property 11: Customer Position Persistence**
    - **Validates: Requirements 5.5**

- [x] 19. Implement NAVIGATING_TO_WAREHOUSE state behavior
  - [x] 19.1 Implement update_navigating_to_warehouse_state() method
    - Navigate to warehouse loading zone coordinates from config
    - Send moving LED animation command
    - Monitor navigation progress
    - Transition to LOADING when goal reached
    - Handle navigation errors
    - _Requirements: 4.1, 4.2, 4.5_

- [x] 20. Implement LOADING state behavior
  - [x] 20.1 Implement update_loading_state() method
    - Play order number announcement audio
    - Open box mechanism
    - Send waiting LED animation command
    - Wait for loading confirmation (keyboard input or timeout)
    - On confirmation: close box, transition to RETURNING_TO_CUSTOMER
    - Handle loading timeout (60 seconds)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [ ]* 20.2 Write unit tests for loading state
    - Test order announcement
    - Test box opening
    - Test loading confirmation handling
    - Test timeout handling
    - _Requirements: 5.1, 5.2, 5.4_

- [x] 21. Implement RETURNING_TO_CUSTOMER state behavior
  - [x] 21.1 Implement update_returning_to_customer_state() method
    - Navigate to stored customer coordinates
    - Send moving LED animation command
    - Monitor navigation progress
    - Transition to DELIVERING when goal reached
    - Handle navigation errors
    - _Requirements: 6.1, 6.2, 6.5_

- [x] 22. Implement DELIVERING state behavior
  - [x] 22.1 Implement update_delivering_state() method
    - Play delivery greeting audio
    - Open box mechanism
    - Start 10-second timer
    - Send waiting LED animation command
    - When timer expires: close box, transition to RESETTING
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 22.2 Write property test for delivery timeout
    - **Property 22: Delivery Timeout**
    - **Validates: Requirements 7.3**

- [x] 23. Implement RESETTING state behavior
  - [x] 23.1 Implement update_resetting_state() method
    - Navigate to home position (0,0)
    - Send moving LED animation command
    - Transition to WAITING when home reached
    - Clear stored customer position and order_id
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ]* 23.2 Write property test for home position return
    - **Property 1: Home Position Return**
    - **Validates: Requirements 1.1, 8.2**

- [x] 24. Implement ERROR_RECOVERY state behavior
  - [x] 24.1 Implement update_error_recovery_state() method
    - Stop all movement
    - Close box if open
    - Play error audio notification
    - Log detailed error information
    - Navigate to home position (0,0)
    - Transition to WAITING when home reached
    - Handle recovery failure (emergency stop after 3 attempts)
    - _Requirements: 10.3, 10.5_
  
  - [ ]* 24.2 Write property test for error recovery to home
    - **Property 13: Error Recovery to Home**
    - **Validates: Requirements 10.3, 10.5**
  
  - [ ]* 24.3 Write unit tests for error handling
    - Test various error conditions
    - Test error logging
    - Test recovery attempts
    - _Requirements: 10.3, 10.5_

- [x] 25. Implement main state machine update loop
  - [x] 25.1 Implement update() method with state dispatch
    - Call appropriate update_*_state() method based on current state
    - Handle exceptions and call handle_error()
    - Update localization continuously
    - Log state machine activity
    - _Requirements: 10.2, 10.3_
  
  - [ ]* 25.2 Write unit tests for state dispatch
    - Test update() calls correct state handler
    - Test exception handling
    - _Requirements: 10.3_

- [x] 26. Checkpoint - Ensure state machine tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 27. Extend Arduino code for hardware control
  - [x] 27.1 Modify ideal_program.ino for motor control
    - Add motor control variables and pin setup
    - Implement parseMotorCommand() parsing MOTOR: commands
    - Implement setMotorSpeed() controlling PWM and direction pins
    - Add motor control to main loop
    - _Requirements: 12.2_
  
  - [x] 27.2 Add servo control to Arduino
    - Include Servo library
    - Add servo object and pin definition
    - Implement parseServoCommand() parsing SERVO: commands
    - Implement setServoAngle() controlling servo position
    - _Requirements: 15.1, 15.2_
  
  - [x] 27.3 Add encoder reading to Arduino
    - Define encoder pins and tick counters
    - Implement interrupt service routines for encoder ticks
    - Implement sendEncoderData() sending tick counts to Raspberry Pi
    - Add periodic encoder reporting to main loop
    - _Requirements: 11.5_
  
  - [x] 27.4 Add IR sensor reading to Arduino
    - Define IR sensor pin
    - Implement readIRSensor() reading analog distance value
    - Implement sendIRData() sending distance to Raspberry Pi
    - Add periodic IR reporting to main loop
    - _Requirements: 11.6_
  
  - [x] 27.5 Extend command parsing in Arduino
    - Modify parseCommand() to handle all new command types
    - Add LED command handlers (LED_IDLE, LED_WAITING, LED_MOVING)
    - Maintain existing SUCCESS_SCAN and FAILURE_SCAN handlers
    - Add command acknowledgment (ACK) responses
    - _Requirements: 12.3, 12.4, 12.5_
  
  - [ ]* 27.6 Write property test for motor command latency
    - **Property 17: Motor Command Latency**
    - **Validates: Requirements 12.2**

- [x] 28. Update main.py for state machine integration
  - [x] 28.1 Rewrite main.py to initialize and run state machine
    - Import all new modules (state_machine, navigation, lidar_interface, odometry, audio_system, box_controller)
    - Initialize serial communication (existing)
    - Initialize database (existing)
    - Initialize LiDAR interface
    - Initialize odometry system
    - Initialize navigation system with map file
    - Initialize audio system
    - Initialize box controller
    - Initialize order verification system
    - Initialize state machine with all subsystems
    - Run main loop calling state_machine.update() at 10Hz
    - Add graceful shutdown handling
    - _Requirements: 14.5_
  
  - [ ]* 28.2 Write integration test for full delivery cycle
    - Test complete workflow: waiting → approach → verify → warehouse → load → return → deliver → reset
    - Use mock hardware for automated testing
    - _Requirements: 1.1, 2.2, 3.5, 4.5, 5.4, 6.5, 7.5, 8.2_

- [x] 29. Create environment map file
  - [x] 29.1 Create assets/maps/warehouse_map.yaml
    - Define occupancy grid dimensions and resolution
    - Mark static obstacles (walls, shelves, equipment)
    - Define delivery zone boundaries
    - Define warehouse loading zone location
    - Define home position (0,0)
    - Add comments explaining coordinate system
    - _Requirements: 9.6_

- [x] 30. Create audio files
  - [x] 30.1 Record or generate Russian audio prompts
    - Create request_qr.wav: "Пожалуйста, покажите QR код вашего заказа"
    - Create order_accepted.wav: "Заказ принят. Еду на склад."
    - Create order_rejected.wav: "Заказ не найден. Пожалуйста, проверьте QR код."
    - Create delivery_greeting.wav: "Ваш заказ доставлен. Приятного дня!"
    - Create order number audio files (order_1.wav through order_100.wav)
    - Place all files in assets/audio/ directory
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 31. Implement comprehensive error handling
  - [x] 31.1 Add error handling to navigation system
    - Handle localization failure (particle filter divergence)
    - Handle path planning failure (no valid path)
    - Handle goal unreachable (stuck detection)
    - Handle obstacle collision (IR sensor emergency stop)
    - Add retry logic with exponential backoff
    - Raise exceptions for state machine error recovery
    - _Requirements: 10.3, 10.5_
  
  - [x] 31.2 Add error handling to sensor systems
    - Handle LiDAR connection loss (reconnection attempts)
    - Handle camera failure (graceful degradation)
    - Handle encoder failure (switch to LiDAR-only localization)
    - Log all sensor errors with timestamps
    - _Requirements: 10.3_
  
  - [x] 31.3 Add error handling to communication
    - Handle serial timeout (retry with backoff)
    - Handle command queue overflow (drop old commands)
    - Handle database connection failure (retry logic)
    - Handle database query timeout (5-second limit)
    - _Requirements: 10.3_
  
  - [x] 31.4 Add error handling to hardware control
    - Handle servo failure (retry and log)
    - Handle motor failure (emergency stop)
    - Add state timeout detection for all states
    - Implement emergency stop state for critical failures
    - _Requirements: 15.6_

- [x] 32. Add comprehensive logging
  - [x] 32.1 Set up Python logging configuration
    - Configure logging to file and console
    - Set log levels (DEBUG for development, INFO for production)
    - Add timestamps and module names to log entries
    - Create separate log files for different subsystems
    - _Requirements: 10.2_
  
  - [x] 32.2 Add logging to all modules
    - Log state transitions with old/new state
    - Log navigation events (path planning, goal reached, obstacles)
    - Log sensor data (person detection, LiDAR scans, encoder ticks)
    - Log order verification results
    - Log audio playback events
    - Log hardware commands (motor, servo, LED)
    - Log all errors with stack traces
    - _Requirements: 10.2_

- [x] 33. Final checkpoint - Integration testing
  - [x] 33.1 Run all unit tests
    - Verify all unit tests pass
    - Check test coverage (aim for >80%)
    - _Requirements: All_
  
  - [x] 33.2 Run all property tests
    - Verify all 25 property tests pass with 100 iterations
    - Check for any edge cases found by property testing
    - _Requirements: All_
  
  - [ ]* 33.3 Run integration tests with hardware
    - Test with actual Arduino, motors, servo, LiDAR
    - Test full delivery cycle in physical environment
    - Test error recovery scenarios
    - Test person detection and tracking
    - Test navigation accuracy with real sensors
    - _Requirements: All_
  
  - [x] 33.4 Performance testing and optimization
    - Measure localization update rate (should be ≥10Hz)
    - Measure navigation accuracy (should be ≤10cm)
    - Measure motor command latency (should be ≤100ms)
    - Optimize any bottlenecks found
    - _Requirements: 9.2, 9.7, 12.2_

- [ ] 34. Documentation and deployment
  - [-] 34.1 Create user documentation
    - Write setup instructions (hardware assembly, software installation)
    - Write calibration guide (wheel measurements, encoder calibration, LiDAR positioning)
    - Write operation manual (starting system, monitoring, troubleshooting)
    - Document configuration parameters in config.py
    - _Requirements: 14.2_
  
  - [~] 34.2 Create developer documentation
    - Document module interfaces and dependencies
    - Document state machine behavior and transitions
    - Document navigation system architecture
    - Document testing strategy and running tests
    - Add Russian comments to all functions as required
    - _Requirements: 14.2_
  
  - [~] 34.3 Prepare deployment package
    - Create installation script
    - Create systemd service file for auto-start
    - Create backup and restore scripts
    - Test deployment on fresh Raspberry Pi
    - _Requirements: 14.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties across randomized inputs
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end system behavior with hardware
- Russian comments should be added to all functions as specified in requirements
- Existing code (qrScanner.py, serialConnection.py, db modules, ideal_program.ino) should be modified minimally
- All new modules should import and use existing modules where appropriate
- Configuration parameters should be centralized in config.py
- Error handling should be comprehensive with graceful degradation
- Logging should be detailed for debugging and monitoring
