import os


MODE = os.environ.get("PTCG_AGENT_MODE", "CABT_SUBMISSION_MODE")

VALID_MODES = [
    "CABT_SUBMISSION_MODE",
    "LOCAL_SIM_TEST_MODE",
]

SUBMISSION_SAFE = True
ENABLE_SCREEN_READING = False
ENABLE_UI_AUTOMATION = False
ENABLE_MOUSE_CONTROL = False
ENABLE_KEYBOARD_CONTROL = False
ENABLE_AUTO_PLAY = False
ENABLE_MEMORY = False
ENABLE_MEMORY_FILE_WRITES = False
ENABLE_DEBUG_LOGS = False
ENABLE_DEBUG_SCREENSHOTS = False

FORBIDDEN_SUBMISSION_IMPORTS = [
    "pyautogui",
    "selenium",
    "cv2",
    "pytesseract",
    "PIL.ImageGrab",
    "Quartz",
    "AppKit",
]

if MODE not in VALID_MODES:
    raise ValueError(f"Invalid agent MODE: {MODE}")

if MODE == "CABT_SUBMISSION_MODE":
    SUBMISSION_SAFE = True
    ENABLE_SCREEN_READING = False
    ENABLE_UI_AUTOMATION = False
    ENABLE_MOUSE_CONTROL = False
    ENABLE_KEYBOARD_CONTROL = False
    ENABLE_AUTO_PLAY = False
    ENABLE_MEMORY_FILE_WRITES = False


def assert_submission_safe() -> None:
    if MODE != "CABT_SUBMISSION_MODE":
        return
    if not SUBMISSION_SAFE:
        raise RuntimeError("CABT_SUBMISSION_MODE requires SUBMISSION_SAFE=True")
    if ENABLE_UI_AUTOMATION:
        raise RuntimeError("CABT_SUBMISSION_MODE forbids UI automation")
