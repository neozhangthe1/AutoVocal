from AutoVocal.maryclient_http import maryclient
from xml.etree import ElementTree as ET
import mido
import mido.messages
import requests
from AutoVocal.syllable import Syllable

VOWELS = "A{6QE@3IO29&U}VY=~"


def generate_song():
    client = maryclient()
    client.set_audio("WAVE_FILE")
    params = client.generate("happy birthday to you happy birthday to you happy birthday dear baby happy birthday to you",
                             "TEXT", "ACOUSTPARAMS", "cmu-rms-hsmm")
    ET.register_namespace('', "http://mary.dfki.de/2002/MaryXML")
    root = ET.fromstring(params)
    word_nodes = root.findall(".//{http://mary.dfki.de/2002/MaryXML}t")
    syllable_nodes = root.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")

    rhythms, pitches, velocities = parse_midi()
    syllables = generate_syllables(syllable_nodes, word_nodes, rhythms, pitches)
    new_nodes = modify_xml(syllables, word_nodes)

    wraper_node = root.find(".//{http://mary.dfki.de/2002/MaryXML}phrase")
    for n in new_nodes:
        wraper_node.insert(n[0], n[1])

    sound = client.generate(ET.tostring(root).decode("utf-8"), "ACOUSTPARAMS", "AUDIO", "cmu-rms-hsmm")
    with open("results/starwars_happy_vocal.wav", "wb") as f_out:
        f_out.write(sound)


def tempo_to_bpm(tempo):
    return int(1 / (float(tempo) / 1000000 / 60))

def bpm_to_tempo(bpm):
    return 1.0 / bpm * 60 * 1000 * 1000


def parse_midi():
    mid = mido.MidiFile("data/music/starwars_tune_cut2.mid")
    track = mid.tracks[0]
    rhythms = []
    pitches = []
    velocities = []
    cur_time = 0
    cur_pitch = 0
    cur_velocity = 0
    tempo = 1.0 / 104 * 60000000
    time_per_tick = get_time_per_tick(tempo, mid.ticks_per_beat)
    for m in track:
        real_time = round(m.time * time_per_tick)
        # print(m.type, m.time, real_time, round(time_per_tick, 3), cur_time, tempo_to_bpm(tempo))
        if type(m) is mido.messages.Message:
            if m.type == "note_on" and m.velocity > 0:
                cur_pitch = m.note
                cur_velocity = m.velocity
            elif m.type == "note_off" or (m.type == "note_on" and m.velocity == 0):
                rhythms.append((cur_time, real_time))
                pitches.append((cur_pitch, m.note))
                velocities.append((cur_velocity, m.velocity))
        elif m.type == 'set_tempo':
            tempo = m.tempo
            time_per_tick = get_time_per_tick(tempo, mid.ticks_per_beat)
        cur_time += real_time

    return rhythms, pitches, velocities


def pitch_to_freq(d):
    return 2 ** ((d - 69) / 12) * 440 / 4


def get_time_per_tick(tempo, ticks_per_beat):
    # default tempo is 500000 microseconds per beat (quarter note)
    # 120 bpm
    return float(tempo) / 1000 / ticks_per_beat


def generate_syllables(syllable_nodes, word_nodes, rhythms, pitches):
    tempo = 120
    syllables = []
    offset = 0
    cur_time = 0

    for i, w in enumerate(word_nodes):
        cur_syl_elements = w.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")
        for s in cur_syl_elements:
            prefix = rhythms[offset][0] - cur_time
            print(i, offset, w.text, cur_time, prefix, rhythms[offset])
            if prefix > 0:
                syllables.append(prefix)
            syllable = Syllable(pitch_to_freq(pitches[offset][0]), rhythms[offset][1], tempo)
            syllables.append((offset, syllable))
            cur_time = rhythms[offset][0] + rhythms[offset][1]
            offset += 1
    return syllables


def modify_xml(syllables, nodes):
    new_nodes = []
    offset = 0  # offset of syllable
    w_offset = 0  # offset of the syllable that current node will be inserted after
    for w in nodes:
        # insert a silent node before a word
        if type(syllables[offset]) is int:
            dummy_node = ET.fromstring('<boundary breakindex="5" duration="%s"/>' % syllables[offset])
            new_nodes.append((w_offset, dummy_node))
            offset += 1
            w_offset += 1
        for s in w.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable"):
            total_duration = 0
            durations = []
            syl = syllables[offset]
            note_duration = syl[1].duration
            offset += 1

            if len(syllables) > offset and type(syllables[offset]) is int:
                note_duration += syllables[offset]
                offset += 1

            phoneme_nodes = s.findall(".//{http://mary.dfki.de/2002/MaryXML}ph")
            for p in phoneme_nodes:
                phoneme_duration = int(p.attrib["d"])
                for ch in p.attrib["p"]:
                    if ch.upper() in VOWELS.upper():
                        phoneme_duration *= 2
                durations.append(phoneme_duration)
                total_duration += phoneme_duration

            for j, d in enumerate(durations):
                percentage = float(d) / total_duration
                durations[j] = round(percentage * note_duration)

            for j, p in enumerate(phoneme_nodes):
                p.attrib["d"] = str(durations[j])
                p.attrib["f0"] = "(1,%s)(100,%s)" % (syl[1].pitch, syl[1].pitch)
        w_offset += 1

    return new_nodes
