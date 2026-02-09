import cv2
from playsound3 import playsound
from db.functions import check_order
import serialConnection


def qr_scanner():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()

    last_data = None

    while True:
        ret, frame = cap.read()
        data, bbox, _ = detector.detectAndDecode(frame)

        if bbox is not None:
            for i in range(len(bbox)):
                pt1 = tuple(map(int, bbox[i][0]))
                pt2 = tuple(map(int, bbox[(i + 1) % len(bbox)][0]))
                cv2.line(frame, pt1, pt2, color=(255, 0, 0), thickness=2)

            if data:
                cv2.putText(frame, data, (int(bbox[0][0][0]), int(bbox[0][0][1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                if data != last_data:
                    last_data = data
                    if check_order(data):
                        playsound('assets/successScan.wav')
                        serialConnection.ser.write(b"SUCCESS_SCAN\n")
                    else:
                        playsound("assets/failureScan.wav")
                        serialConnection.ser.write(b"FAILURE_SCAN\n")

        cv2.imshow("QR Scanner", frame)
        if cv2.waitKey(10) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
