# Requirements Document

## Introduction

RelayBot is an autonomous delivery robot system designed to operate in a fixed warehouse/delivery zone environment. The system uses Arduino and Raspberry Pi hardware to provide automated order delivery services. The robot navigates between fixed coordinate positions, detects customers using LiDAR, verifies orders through QR codes or verbal input, travels to a warehouse loading zone, and delivers packages to customers.

The system integrates existing components (QR scanner, SQLite database, Arduino LED control) with new autonomous navigation, state machine control, and sensor integration capabilities.

## Glossary

- **RelayBot**: The complete autonomous delivery robot system including hardware and software
- **Delivery_Zone**: The designated area where customers wait for deliveries (contains home position at 0,0)
- **Warehouse_Loading_Zone**: Fixed coordinate location where warehouse staff load packages onto the robot
- **Home_Position**: The robot's default waiting location at coordinates (0,0) in the delivery zone
- **Navigation_System**: The subsystem responsible for localization, path planning, and movement control
- **State_Machine**: The control system managing robot behavior states and transitions
- **LiDAR_System**: LDROBOT D500 sensor used for person detection and navigation
- **Order_Verification_System**: Subsystem handling QR code scanning and database validation
- **Customer**: Person in the delivery zone requesting package delivery
- **Warehouse_Staff**: Personnel responsible for loading packages at the warehouse loading zone
- **Odometry_System**: System tracking robot position and orientation through wheel encoders or sensor fusion
- **Audio_System**: Voice/sound feedback system for customer and staff interaction
- **Box_Mechanism**: Servo-controlled compartment for secure package storage and delivery

## Requirements

### Requirement 1: Robot Waiting State

**User Story:** As a delivery system, I want the robot to wait at a designated home position when idle, so that it is ready to respond to customer arrivals.

#### Acceptance Criteria

1. WHEN the robot completes a delivery cycle or starts up, THE State_Machine SHALL move the robot to Home_Position at coordinates (0,0)
2. WHILE at Home_Position, THE State_Machine SHALL monitor the LiDAR_System for person detection
3. WHILE waiting at Home_Position, THE RelayBot SHALL display idle eye animations through the LED system
4. WHEN the robot is at Home_Position, THE Navigation_System SHALL maintain position accuracy within 10cm of (0,0)

### Requirement 2: Customer Detection and Approach

**User Story:** As a customer, I want the robot to detect my presence and approach me when I enter the delivery zone, so that I can request a delivery.

#### Acceptance Criteria

1. WHEN a person enters the Delivery_Zone, THE LiDAR_System SHALL detect the person's presence and position
2. WHEN a person is detected in the Delivery_Zone, THE State_Machine SHALL transition from waiting state to approach state
3. WHEN approaching a customer, THE Navigation_System SHALL calculate and execute a path to the customer's position
4. WHILE approaching, THE LiDAR_System SHALL continuously track the customer's position
5. IF the customer disappears from the Delivery_Zone, THEN THE State_Machine SHALL stop movement and return to waiting state
6. WHEN the robot reaches within 50cm of the customer, THE State_Machine SHALL stop and transition to order verification state

### Requirement 3: Order Verification

**User Story:** As a customer, I want to verify my order using a QR code or verbal order number, so that the robot can retrieve my package.

#### Acceptance Criteria

1. WHEN the robot stops at the customer position, THE Audio_System SHALL request the customer to present a QR code or provide an order number
2. WHEN a QR code is presented, THE Order_Verification_System SHALL scan and decode the QR code data
3. WHEN QR code data is received, THE Order_Verification_System SHALL parse the order_id and secret_key from the JSON payload
4. WHEN order credentials are obtained, THE Order_Verification_System SHALL query the database to validate the order
5. IF the order is valid, THEN THE State_Machine SHALL transition to warehouse navigation state and THE Audio_System SHALL confirm order acceptance
6. IF the order is invalid, THEN THE State_Machine SHALL reject the order, THE Audio_System SHALL notify the customer, and THE State_Machine SHALL return to waiting state
7. WHERE verbal order number input is supported, THE Audio_System SHALL accept spoken order numbers and validate them against the database

### Requirement 4: Warehouse Navigation

**User Story:** As a warehouse operator, I want the robot to navigate autonomously to the loading zone when an order is verified, so that I can load the package efficiently.

#### Acceptance Criteria

1. WHEN an order is verified, THE Navigation_System SHALL plan a path from the current position to the Warehouse_Loading_Zone coordinates
2. WHEN navigating to the warehouse, THE Navigation_System SHALL use localization data to maintain accurate position tracking
3. WHILE navigating, THE Navigation_System SHALL avoid obstacles detected by the LiDAR_System
4. WHEN the robot reaches the Warehouse_Loading_Zone, THE Navigation_System SHALL stop within 10cm of the target coordinates
5. WHEN stopped at the loading zone, THE State_Machine SHALL transition to loading state

### Requirement 5: Package Loading

**User Story:** As warehouse staff, I want the robot to announce the order number and wait for me to load the package, so that I can prepare the correct order.

#### Acceptance Criteria

1. WHEN the robot arrives at the Warehouse_Loading_Zone, THE Audio_System SHALL announce the order number
2. WHILE in loading state, THE State_Machine SHALL keep the Box_Mechanism open for package placement
3. WHILE waiting for loading, THE RelayBot SHALL display waiting animations through the LED system
4. WHEN Warehouse_Staff confirms loading completion, THE State_Machine SHALL close the Box_Mechanism and transition to return delivery state
5. THE State_Machine SHALL store the customer's original coordinates for return navigation

### Requirement 6: Return Delivery Navigation

**User Story:** As a customer, I want the robot to return to my exact location after loading, so that I can receive my package without moving.

#### Acceptance Criteria

1. WHEN loading is confirmed, THE Navigation_System SHALL plan a path to the stored customer coordinates
2. WHEN navigating back to the customer, THE Navigation_System SHALL use the same localization system to reach the exact pickup coordinates
3. WHILE returning, THE Navigation_System SHALL avoid obstacles detected by the LiDAR_System
4. WHEN the robot reaches the customer coordinates, THE Navigation_System SHALL stop within 10cm of the target position
5. WHEN stopped at customer position, THE State_Machine SHALL transition to delivery completion state

### Requirement 7: Delivery Completion

**User Story:** As a customer, I want the robot to open the box and allow me to retrieve my package, so that I can complete the delivery transaction.

#### Acceptance Criteria

1. WHEN the robot reaches the customer position, THE Audio_System SHALL greet the customer and announce delivery
2. WHEN delivery is announced, THE Box_Mechanism SHALL open the compartment using the servo motor
3. WHILE the box is open, THE State_Machine SHALL wait for 10 seconds to allow package retrieval
4. WHEN 10 seconds elapse, THE Box_Mechanism SHALL close the compartment
5. WHEN the box is closed, THE State_Machine SHALL transition to reset state

### Requirement 8: System Reset

**User Story:** As a delivery system, I want the robot to return to home position after completing a delivery, so that it is ready for the next customer.

#### Acceptance Criteria

1. WHEN delivery is complete, THE Navigation_System SHALL plan a path back to Home_Position at (0,0)
2. WHEN the robot reaches Home_Position, THE State_Machine SHALL transition to waiting state
3. WHEN returning to waiting state, THE RelayBot SHALL display idle animations through the LED system

### Requirement 9: Navigation System Implementation

**User Story:** As a system architect, I want a reliable navigation system that provides accurate localization in the fixed environment, so that the robot can navigate between all required positions.

#### Acceptance Criteria

1. THE Navigation_System SHALL provide absolute position coordinates relative to the global origin (0,0)
2. THE Navigation_System SHALL maintain position accuracy within 10cm for all navigation tasks
3. THE Navigation_System SHALL support path planning between arbitrary coordinates in the environment
4. THE Navigation_System SHALL integrate with the Odometry_System for position tracking
5. WHERE ArUco markers are used, THE Navigation_System SHALL use camera-based localization with wall/floor markers
6. WHERE pure LiDAR navigation is used, THE Navigation_System SHALL use SLAM or known map-based localization
7. THE Navigation_System SHALL provide real-time position updates at minimum 10Hz frequency

### Requirement 10: State Machine Architecture

**User Story:** As a system architect, I want a clear state machine controlling robot behavior, so that the system is maintainable and predictable.

#### Acceptance Criteria

1. THE State_Machine SHALL implement distinct states: Waiting, Approaching, Verifying, NavigatingToWarehouse, Loading, ReturningToCustomer, Delivering, Resetting
2. WHEN transitioning between states, THE State_Machine SHALL log state changes for debugging
3. WHEN in any state, THE State_Machine SHALL handle error conditions and transition to safe states
4. THE State_Machine SHALL coordinate actions between Navigation_System, Audio_System, Order_Verification_System, and Box_Mechanism
5. WHEN an error occurs, THE State_Machine SHALL return the robot to Home_Position safely

### Requirement 11: Sensor Integration

**User Story:** As a system integrator, I want all sensors properly integrated with the control system, so that the robot can perceive its environment accurately.

#### Acceptance Criteria

1. THE LiDAR_System SHALL provide continuous 360-degree scanning data at minimum 10Hz
2. WHEN a person is detected, THE LiDAR_System SHALL provide the person's position relative to the robot
3. THE LiDAR_System SHALL filter noise and provide reliable obstacle detection within 5 meters
4. WHERE camera-based navigation is used, THE Navigation_System SHALL process camera frames at minimum 15fps
5. THE Odometry_System SHALL track wheel rotations and calculate position changes
6. THE IR_Sensor SHALL detect obstacles in the robot's immediate path (within 30cm)

### Requirement 12: Arduino-Raspberry Pi Communication

**User Story:** As a system integrator, I want reliable communication between Raspberry Pi and Arduino, so that motor control and LED feedback work correctly.

#### Acceptance Criteria

1. THE RelayBot SHALL maintain serial communication between Raspberry Pi and Arduino at 9600 baud
2. WHEN the Raspberry Pi sends motor commands, THE Arduino SHALL execute speed and direction changes within 100ms
3. WHEN state changes occur, THE Raspberry Pi SHALL send LED animation commands to the Arduino
4. WHEN the Arduino receives LED commands, THE Arduino SHALL display the appropriate eye animation
5. THE communication protocol SHALL handle command queuing to prevent message loss

### Requirement 13: Audio Feedback System

**User Story:** As a user (customer or warehouse staff), I want clear audio feedback from the robot, so that I understand what actions to take.

#### Acceptance Criteria

1. WHEN requesting order verification, THE Audio_System SHALL play a clear voice prompt in Russian
2. WHEN an order is verified successfully, THE Audio_System SHALL play a success sound
3. WHEN an order verification fails, THE Audio_System SHALL play a failure sound and explain the issue
4. WHEN arriving at the loading zone, THE Audio_System SHALL announce the order number clearly
5. WHEN delivering to the customer, THE Audio_System SHALL greet the customer and announce delivery completion
6. THE Audio_System SHALL use pre-recorded audio files or text-to-speech for all announcements

### Requirement 14: Code Quality and Documentation

**User Story:** As a developer, I want well-documented, modular code with Russian comments, so that the system is maintainable and understandable.

#### Acceptance Criteria

1. THE RelayBot SHALL organize code into separate modules: navigation, state_machine, sensors, communication, audio, database
2. WHEN writing functions, THE developer SHALL include Russian comments explaining purpose and parameters
3. THE code SHALL follow Python PEP 8 style guidelines for Python modules
4. THE code SHALL follow Arduino style guidelines for Arduino sketches
5. THE RelayBot SHALL integrate with existing modules: qrScanner.py, serialConnection.py, db modules, ideal_program.ino
6. WHEN adding new functionality, THE developer SHALL minimize modifications to existing working code

### Requirement 15: Box Mechanism Control

**User Story:** As a system operator, I want reliable control of the package compartment, so that packages are secured during transport and accessible during delivery.

#### Acceptance Criteria

1. WHEN loading begins, THE Box_Mechanism SHALL open the compartment to 90 degrees using the servo motor
2. WHEN loading is confirmed, THE Box_Mechanism SHALL close the compartment to 0 degrees
3. WHEN delivering to customer, THE Box_Mechanism SHALL open the compartment to 90 degrees
4. WHEN delivery timeout expires, THE Box_Mechanism SHALL close the compartment to 0 degrees
5. THE Box_Mechanism SHALL move smoothly to prevent package damage
6. IF servo control fails, THEN THE State_Machine SHALL log an error and attempt recovery
