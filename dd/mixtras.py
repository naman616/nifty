engine = pyttsx3.init()
rate = engine.getProperty('rate')
engine.setProperty('rate', 150)  # Slower
engine.say("This is slower speech.")
engine.runAndWait()