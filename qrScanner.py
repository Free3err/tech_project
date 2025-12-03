import cv2
import simpleaudio as sa

from db.functions import check_order


def qr_scanner():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()
    print("Camera has initialized!")

    while True:
        ret, frame = cap.read()
        data, bbox, _ = detector.detectAndDecode(frame)

        if bbox is not None:
            for i in range(len(bbox)):
                pt1 = tuple(map(int, bbox[i][0]))
                pt2 = tuple(map(int, bbox[(i + 1) % len(bbox)][0]))
                cv2.line(frame, pt1, pt2, color=(255, 0, 0), thickness=2)

            if data:
                print(data)
                if check_order(data):
                    wave_obj = sa.WaveObject.from_wave_file("assets/scanMusic.wav")
                    play_obj = wave_obj.play()
                    play_obj.wait_done()
                else:
                    print("QR scan failed")

        if cv2.waitKey(10) & 0xFF == 27:
            break

    cap.release()
