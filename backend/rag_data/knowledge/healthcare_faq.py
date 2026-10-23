#!/usr/bin/env python3
"""
Generate a sample PDF knowledge base for testing the RAG system.
Run this script to create healthcare_faq.pdf in the current directory.
"""

import fitz  # PyMuPDF
import os

# Ensure knowledge directory exists
os.makedirs("knowledge", exist_ok=True)

# Create a simple PDF using fitz
doc = fitz.open()

# Add a title page
page = doc.new_page()
title_text = "Healthcare Assistant FAQ"
title_rect = fitz.Rect(72, 72, 500, 100)
page.insert_textbox(title_rect, title_text, fontsize=24, color=(0, 0, 0.8))

# Add a subtitle
subtitle_text = "Frequently Asked Questions for Healthcare Robot Assistant"
subtitle_rect = fitz.Rect(72, 110, 500, 130)
page.insert_textbox(subtitle_rect, subtitle_text, fontsize=14, color=(0.3, 0.3, 0.3))

# Add table of contents
toc = [
    ("1. General Information", 5),
    ("2. Vitals Monitoring", 7),
    ("3. Medication Reminders", 9),
    ("4. Emergency Procedures", 11),
    ("5. Privacy & Safety", 13),
]

toc_y = 160
for i, (item, page_num) in enumerate(toc):
    y_pos = toc_y + i * 20
    page.insert_text((72, y_pos), item, fontsize=11)
    page.insert_text((500, y_pos), str(page_num), fontsize=11)

# Add content pages with questions and answers
y = 100
questions_page5 = [
    ("What is this healthcare assistant robot?", 
     "This is an intelligent robotic assistant designed to support patients with routine care tasks, including medication reminders, vital signs monitoring, and basic companionship."),
    ("Who can use this healthcare robot?",
     "The robot is designed for use by patients in healthcare facilities or home care settings, particularly elderly or recovering patients who need assistance with daily routines."),
    ("How do I activate the robot's voice assistant?",
     "Press the microphone button on the robot's interface or say a wake word. The robot will listen for your voice command and respond using its text-to-speech system."),
    ("What languages does the robot support?",
     "Currently, the robot supports English for voice interaction. Future updates may add support for additional languages based on user demand."),
]

for i, (q, a) in enumerate(questions_page5):
    page.insert_text((72, y), f"Q: {q}", fontsize=11, color=(0, 0.2, 0.4))
    y += 20
    page.insert_text((80, y), f"A: {a}", fontsize=10)
    y += 35

# Page 6: Vitals Monitoring
page6 = doc.new_page()
page6.insert_text((72, 72), "2. Vitals Monitoring", fontsize=18)
y = 100
questions_page6 = [
    ("What vital signs does the robot monitor?",
     "The robot continuously monitors heart rate (beats per minute) and blood oxygen saturation (SpO2) using a non-invasive optical sensor placed on the finger."),
    ("How accurate are the vitals measurements?",
     "The robot provides estimates based on photoplethysmography (PPG) technology. Measurements are for wellness tracking only and should not replace professional medical equipment."),
    ("How do I take my vitals with the robot?",
     "Place your finger on the MAX30102 sensor on the robot's interface. Hold still for 15-30 seconds while the robot captures and displays your heart rate and SpO2 readings."),
    ("What is a normal heart rate and SpO2 level?",
     "A normal resting heart rate for adults is 60-100 BPM. Normal SpO2 levels are typically 95-100%. Consult your healthcare provider for personalized ranges."),
]

for i, (q, a) in enumerate(questions_page6):
    page6.insert_text((72, y), f"Q: {q}", fontsize=11, color=(0, 0.2, 0.4))
    y += 20
    page6.insert_text((80, y), f"A: {a}", fontsize=10)
    y += 35

# Page 7: Medication Reminders
page7 = doc.new_page()
page7.insert_text((72, 72), "3. Medication Reminders", fontsize=18)
y = 100
questions_page7 = [
    ("How do medication reminders work?",
     "You can set up medication reminders through the robot's interface or voice commands. The robot will notify you when it's time to take your prescribed medications."),
    ("What should I do if I miss a medication reminder?",
     "If you miss a reminder, the robot will log the event and notify your caregiver if configured to do so. Take your medication as soon as possible and consult your healthcare provider if needed."),
    ("Can the robot help me track my medication schedule?",
     "Yes, the robot maintains a medication log and can answer questions about your scheduled doses, timing, and dosages based on the information you provide."),
    ("How do I add or modify medication reminders?",
     "Use the voice command 'Add medication reminder' or access the medication settings through the web dashboard to configure your medication schedule."),
]

for i, (q, a) in enumerate(questions_page7):
    page7.insert_text((72, y), f"Q: {q}", fontsize=11, color=(0, 0.2, 0.4))
    y += 20
    page7.insert_text((80, y), f"A: {a}", fontsize=10)
    y += 35

# Page 8: Emergency Procedures
page8 = doc.new_page()
page8.insert_text((72, 72), "4. Emergency Procedures", fontsize=18)
y = 100
questions_page8 = [
    ("What should I do in a medical emergency?",
     "In a medical emergency, immediately call your local emergency services (911 or local equivalent) or press the emergency call button on the robot's interface."),
    ("Can the robot call emergency services for me?",
     "The robot cannot directly dial emergency services, but it can alert your designated emergency contact through the connected app or web dashboard."),
    ("What information should I provide to emergency responders?",
     "Inform responders about your medical conditions, current medications, allergies, and the last time you took your medications. The robot can assist by providing stored health information."),
    ("How do I activate the emergency alert feature?",
     "Press and hold the emergency button for 3 seconds, or say 'Emergency alert' to activate the emergency notification system."),
]

for i, (q, a) in enumerate(questions_page8):
    page8.insert_text((72, y), f"Q: {q}", fontsize=11, color=(0, 0.2, 0.4))
    y += 20
    page8.insert_text((80, y), f"A: {a}", fontsize=10)
    y += 35

# Page 9: Privacy & Safety
page9 = doc.new_page()
page9.insert_text((72, 72), "5. Privacy & Safety", fontsize=18)
y = 100
questions_page9 = [
    ("Is my personal health information secure?",
     "Yes, the robot uses encryption for data transmission and stores personal information securely. All data is processed in accordance with applicable privacy regulations."),
    ("Who can access my health data?",
     "Your health data is accessible only to authorized users through the web dashboard. Caregivers may be granted access with your permission for remote monitoring."),
    ("Does the robot record all conversations?",
     "No, the robot does not record or store voice conversations. Audio streams are processed in real-time for voice recognition and discarded after processing."),
    ("How do I clear my conversation history?",
     "Use the 'Clear History' option in the settings menu of the web dashboard or say 'Clear conversation history' to remove stored interaction data."),
]

for i, (q, a) in enumerate(questions_page9):
    page9.insert_text((72, y), f"Q: {q}", fontsize=11, color=(0, 0.2, 0.4))
    y += 20
    page9.insert_text((80, y), f"A: {a}", fontsize=10)
    y += 35

# Save the PDF
output_path = "healthcare_faq.pdf"
doc.save(output_path)
doc.close()

print(f"PDF created successfully: {output_path}")
print(f"Total pages: {len(doc)}")
print("This sample FAQ covers:")
print("  - General Information (robot overview, activation, language)")
print("  - Vitals Monitoring (heart rate, SpO2, usage)")
print("  - Medication Reminders (scheduling, tracking)")
print("  - Emergency Procedures (what to do, alert activation)")
print("  - Privacy & Safety (data security, access control)")
