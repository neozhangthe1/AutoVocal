from .maryclient_http import maryclient
from xml.etree import ElementTree as ET
import mido
import mido.messages
from .syllable import Syllable
import math

VOWELS = "A{6QE@3IO29&U}VY=~"


def generate_song():
    client = maryclient()
    client.set_audio("WAVE_FILE")
    params = client.generate("hello world", "TEXT", "ACOUSTPARAMS")
    root = ET.fromstring(params)
    word_nodes = root.findall(".//{http://mary.dfki.de/2002/MaryXML}t")
    syllable_nodes = root.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")

    rhythms, pitches, velocities = parse_midi()
    syllables = generate_syllables(syllable_nodes, word_nodes, rhythms, pitches)
    modify_xml(syllables, syllable_nodes)


def parse_midi():
    mid = mido.MidiFile("../data/music/birthday.mid")
    track = mid.tracks[0]
    rhythms = []
    pitches = []
    velocities = []
    cur_time = 0
    cur_pitch = 0
    cur_velocity = 0
    for m in track:
        if type(m) is mido.messages.Message:
            if m.type == "note_on":
                cur_time += m.time
                cur_pitch = m.note
                cur_velocity = m.velocity
            elif m.type == "note_off":
                rhythms.append((cur_time, m.time))
                pitches.append((cur_pitch, m.note))
                velocities.append((cur_velocity, m.velocity))
                cur_time += m.time
    return rhythms, pitches, velocities


def generate_syllables(syllable_nodes, word_nodes, rhythms, pitches):
    tempo = 120
    syllables = []
    offset = 0
    cur_time = 0

    for i, w in enumerate(word_nodes):
        cur_syl_elements = w.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")
        prefix = rhythms[offset] - cur_time
        syllables.append(prefix)
        for s in cur_syl_elements:
            syllable = Syllable(pitches[offset][0], rhythms[offset][1], tempo)
            syllables.append((offset, syllable))
            cur_time = rhythms[offset][0] + rhythms[offset][1]
            offset += 1
    return syllables


def modify_xml(syllables, nodes):
    durations = []
    total_duration = 0
    for i, node in enumerate(nodes):
        syllable = syllables[i]
        phoneme_nodes = node.findall(".//{http://mary.dfki.de/2002/MaryXML}ph")
        for p in phoneme_nodes:
            phoneme_duration = int(p.attrib["d"])
            for ch in p.attrib["p"]:
                if ch.upper() in VOWELS.upper():
                    phoneme_duration *= 2
            durations.append(phoneme_duration)
            total_duration += phoneme_duration

        for j, d in enumerate(durations):
            percentage = float(d) / total_duration
            durations[i] = round(percentage * syllable.duration)

        for j, p in phoneme_nodes:
            p.attrib["d"] = durations[i]
            p.attrib["f0"] = "(1,%s)(100,%s)" % syllable.pitch

