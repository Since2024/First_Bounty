import cv2
import numpy as np

image_path = 'app/templates/business_front.jpg'
original = cv2.imread(image_path)

zoom = 0.5
offset_x, offset_y = 0, 0
measurements = []
measuring = False
panning = False
start_point = None
current_pos = None

def get_view():
    h, w = original.shape[:2]
    resized = cv2.resize(original, (int(w*zoom), int(h*zoom)))
    canvas = np.ones((900, 1400, 3), dtype=np.uint8) * 50
    
    y1, x1 = max(0, -offset_y), max(0, -offset_x)
    y2 = min(resized.shape[0], canvas.shape[0] - offset_y)
    x2 = min(resized.shape[1], canvas.shape[1] - offset_x)
    
    cy1, cx1 = max(0, offset_y), max(0, offset_x)
    cy2, cx2 = cy1 + (y2-y1), cx1 + (x2-x1)
    
    canvas[cy1:cy2, cx1:cx2] = resized[y1:y2, x1:x2]
    return canvas

def screen_to_img(x, y):
    return int((x - offset_x) / zoom), int((y - offset_y) / zoom)

def mouse(event, x, y, flags, param):
    global start_point, offset_x, offset_y, measurements, measuring, panning, current_pos
    
    current_pos = (x, y)
    
    if event == cv2.EVENT_LBUTTONDOWN:
        if panning:
            # Pan mode
            start_point = (x, y)
        else:
            # Measure mode
            measuring = True
            ix, iy = screen_to_img(x, y)
            start_point = (ix, iy)
    
    elif event == cv2.EVENT_MOUSEMOVE:
        if panning and start_point:
            offset_x += x - start_point[0]
            offset_y += y - start_point[1]
            start_point = (x, y)
    
    elif event == cv2.EVENT_LBUTTONUP:
        if measuring and start_point:
            ix, iy = screen_to_img(x, y)
            x1, y1 = start_point
            x2, y2 = ix, iy
            
            xmin, xmax = min(x1,x2), max(x1,x2)
            ymin, ymax = min(y1,y2), max(y1,y2)
            w, h = xmax-xmin, ymax-ymin
            
            # Scale to template
            tx = int(xmin * 847 / original.shape[1])
            ty = int(ymin * 1197 / original.shape[0])
            tw = int(w * 847 / original.shape[1])
            th = int(h * 1197 / original.shape[0])
            
            measurements.append([tx, ty, tw, th])
            print(f"\n✓ Field #{len(measurements)}: \"px\": [{tx}, {ty}, {tw}, {th}],")
            
            measuring = False
        start_point = None

cv2.namedWindow('Measure')
cv2.setMouseCallback('Measure', mouse)

print("\n" + "="*70)
print("SIMPLE CONTROLS:")
print("  Press 'p' = Toggle PAN mode ON/OFF")
print("  Press 'm' = Toggle MEASURE mode ON/OFF")
print("")
print("  When PAN mode: Left-click & drag to move image")
print("  When MEASURE mode: Left-click & drag to measure field")
print("")
print("  + / - = Zoom")
print("  0 = Reset")
print("  r = Clear")
print("  q = Quit")
print("="*70)
print("\nStarting in MEASURE mode\n")

while True:
    display = get_view()
    
    # Draw saved boxes
    for i, (tx,ty,tw,th) in enumerate(measurements):
        x = int(tx * original.shape[1] / 847 * zoom + offset_x)
        y = int(ty * original.shape[0] / 1197 * zoom + offset_y)
        w = int(tw * original.shape[1] / 847 * zoom)
        h = int(th * original.shape[0] / 1197 * zoom)
        cv2.rectangle(display, (x,y), (x+w,y+h), (0,255,0), 3)
        cv2.putText(display, f"#{i+1}", (x,y-5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    
    # Draw current measurement
    if measuring and start_point and current_pos:
        ix, iy = screen_to_img(*current_pos)
        sx1 = int(start_point[0] * zoom + offset_x)
        sy1 = int(start_point[1] * zoom + offset_y)
        sx2 = int(ix * zoom + offset_x)
        sy2 = int(iy * zoom + offset_y)
        cv2.rectangle(display, (sx1,sy1), (sx2,sy2), (0,0,255), 2)
    
    # Status bar
    mode_text = "PAN" if panning else "MEASURE"
    color = (255,100,100) if panning else (100,255,100)
    status = f"Mode: {mode_text} | Zoom: {zoom:.1f}x | Fields: {len(measurements)}"
    cv2.putText(display, status, (10,30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(display, "Press 'p' for PAN, 'm' for MEASURE", (10,60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
    
    cv2.imshow('Measure', display)
    key = cv2.waitKey(10) & 0xFF
    
    if key == ord('p'):
        panning = True
        measuring = False
        print("→ PAN MODE (press 'm' to measure)")
    elif key == ord('m'):
        panning = False
        measuring = False
        print("→ MEASURE MODE (click & drag)")
    elif key == ord('+') or key == ord('='):
        zoom = min(2.0, zoom + 0.1)
    elif key == ord('-'):
        zoom = max(0.2, zoom - 0.1)
    elif key == ord('0'):
        zoom, offset_x, offset_y = 0.5, 0, 0
    elif key == ord('r'):
        measurements = []
        print("Cleared")
    elif key == ord('q'):
        break

cv2.destroyAllWindows()

if measurements:
    print("\n" + "="*70)
    print("COPY TO JSON:")
    print("="*70)
    for i, bbox in enumerate(measurements):
        print(f'  "px": {bbox},  // Field {i+1}')
    print("="*70)