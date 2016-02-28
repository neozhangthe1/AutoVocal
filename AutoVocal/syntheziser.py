from .maryclient_http import maryclient
from xml.etree import ElementTree as ET
import mido
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
    syllables = generate_syllables(syllable_nodes, word_nodes)
    modify_xml(syllables, syllable_nodes)


def parse_midi():
    mid = mido.MidiFile("../data/music/birthday.mid")
    track = mid.tracks[0]


def get_rhythm():
    pass


def get_pitch():
    pass


def generate_syllables(syllable_nodes, word_nodes):
    tempo = 120
    num_words = len(syllable_nodes)
    syllables = []
    end = False

    for i, w in enumerate(word_nodes):
        if i == num_words - 1:
            end = True
        cur_syllable_elements = w.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")
        for s in cur_syllable_elements:
            pitch = get_pitch()
            duration = get_rhythm()
            syllable = Syllable(pitch, duration, tempo)
            syllables.append(syllable)
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
                if ch.upper() in VOWELS:
                    phoneme_duration *= 2
            durations.append(phoneme_duration)
            total_duration += phoneme_duration

        for j, d in enumerate(durations):
            percentage = float(d) / total_duration
            durations[i] = round(percentage * syllable.duration)

        for j, p in phoneme_nodes:
            p.attrib["d"] = durations[i]
            p.attrib["f0"] = "(1,%s)(100,%s)" % syllable.pitch

