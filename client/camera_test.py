import cv2
import PySimpleGUI as sg

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 24)

layout = [[sg.Image(filename="", key="image")], [sg.Button("Exit")]]
window = sg.Window("PS3 Eye Camera", layout)

while True:
    event, values = window.read(timeout=20)
    if event == "Exit" or event == sg.WIN_CLOSED:
        break
    
    ret, frame = cap.read()
    if ret:
        imgbytes = cv2.imencode(".png", frame)[1].tobytes()
        window["image"].update(data=imgbytes)

cap.release()
window.close()
