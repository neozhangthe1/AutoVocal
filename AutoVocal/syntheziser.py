from AutoVocal.maryclient_http import maryclient
from xml.etree import ElementTree as ET
import mido
import mido.messages
import requests
from AutoVocal.syllable import Syllable
import math
import numpy as np

VOWELS = "A{6QE@3IO29&U}VY=~"


def generate_song():
    client = maryclient()
    client.set_audio("WAVE_FILE")
    texts = "happy birthday to you, happy birthday to you, happy birthday dear baby, happy birthday to you".split(",")[:1]
    params = [client.generate(t,
                             "TEXT", "ACOUSTPARAMS", "cmu-rms-hsmm") for t in texts]
    ET.register_namespace('', "http://mary.dfki.de/2002/MaryXML")
    root = ET.fromstring(params[0])
    word_nodes = root.findall(".//{http://mary.dfki.de/2002/MaryXML}t")
    syllable_nodes = root.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")

    rhythms, pitches, velocities, beats, bars = parse_midi()
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

    tick_per_beat = mid.ticks_per_beat
    beat_offset = 0
    cur_beat = []  # the notes within current beat
    beats = []

    tick_per_bar = mid.ticks_per_beat * 4
    bar_offset = 0  # the number of bar that current note in
    cur_bar = []  # the notes within current bar
    bars = []   # all the bars in the score

    note_offset = 0  # the index of current note in the score
    rhythms = []  # the timestamp of each note
    pitches = []  # the pitch of each note
    velocities = []  # the velocity of each note

    cur_tick = 0
    cur_time = 0
    cur_pitch = 0
    cur_velocity = 0
    pre_time = 0
    tempo = 1.0 / 104 * 60000000
    time_per_tick = get_time_per_tick(tempo, mid.ticks_per_beat)
    for m in track:
        real_time = round(m.time * time_per_tick)
        cur_tick += m.time
        # print(m.type, m.time, real_time, round(time_per_tick, 3), cur_time, tempo_to_bpm(tempo))
        if type(m) is mido.messages.Message:
            if m.type == "note_on" and m.velocity > 0:
                cur_pitch = m.note
                cur_velocity = m.velocity
                print(note_offset, m.time, cur_tick / tick_per_bar, bar_offset)
                if math.floor(cur_tick / tick_per_beat) > beat_offset:
                    beat_offset = math.floor(cur_tick / tick_per_beat)
                    # if len(cur_beat) > 0:
                    beats.append(cur_beat)
                    cur_beat = []
                    if math.floor(cur_tick / tick_per_bar) > bar_offset:
                        bar_offset = math.floor(cur_tick / tick_per_bar)
                        # if len(cur_bar) > 0:
                        bars.append(cur_bar)
                        cur_bar = []
                    cur_bar.append(cur_beat)
                cur_beat.append(note_offset)

                note_offset += 1
            elif m.type == "note_off" or (m.type == "note_on" and m.velocity == 0):
                rhythms.append((cur_time, real_time, cur_time - pre_time))
                pre_time = (cur_time + real_time)
                pitches.append((cur_pitch, m.note))
                velocities.append((cur_velocity, m.velocity))
        elif m.type == 'set_tempo':
            tempo = m.tempo
            time_per_tick = get_time_per_tick(tempo, mid.ticks_per_beat)
        cur_time += real_time

    if len(beats[0]) == 0:
        beats = beats[1:]
    if len(bars[0]) == 0:
        bars = bars[1:]

    return rhythms, pitches, velocities, beats, bars


def pitch_to_freq(d):
    return 2 ** ((d - 69) / 12) * 440 / 4


def get_time_per_tick(tempo, ticks_per_beat):
    # default tempo is 500000 microseconds per beat (quarter note)
    # 120 bpm
    return float(tempo) / 1000 / ticks_per_beat


def generate_silent_node(duration):
    return ET.fromstring('<boundary breakindex="5" duration="%s"/>' % duration)


def generate_phoneme_node(duration, pitch):
    pitch = pitch_to_freq(pitch[0])
    f0 = "(1,%s)(100,%s)" % (pitch, pitch)
    return ET.fromstring('<ph d="%s" end="0.0001" f0="%s" p="l"/>' % (duration, f0))


def get_f0(xs, ys):
    f0 = ""
    for i, y in enumerate(ys):
        f0 += "(%s,%s)" % (xs[i], y)
    return f0


def generate_syllable_node(node, notes, rhythms, pitches, pos):
    vowel_offset = None
    phoneme_nodes = node.findall(".//{http://mary.dfki.de/2002/MaryXML}ph")
    margin = [0, 0]
    for i, p in enumerate(phoneme_nodes):
        is_vowel = False
        for ch in p.attrib["p"]:
            if ch.upper() in VOWELS.upper():
                vowel_offset = i
                is_vowel = True
                break
        if not is_vowel:
            if vowel_offset is None:  # consonant before vowel
                f0 = pitch_to_freq(pitches[notes[0]][0])  # the pitch of the first syllable
                p.attrib["f0"] = "(1,%s)(100,%s)" % (f0, f0)
                margin[0] += int(p.attrib["d"])
            else:  # consonant after vowel
                f0 = pitch_to_freq(pitches[notes[-1]][0])  # the pitch of the last syllable
                p.attrib["f0"] = "(1,%s)(100,%s)" % (f0, f0)
                margin[0] += int(p.attrib["d"])

    # linear interpolation to smooth the pitch
    durations = [rhythms[k][1] for k in notes]
    print(durations)
    vowel_duration = sum(durations)
    percent = 0
    x = [1]
    y = [pitch_to_freq(pitches[notes[0]][0])]
    for i, n in enumerate(notes):
        percent += round(float(durations[i]) / vowel_duration * 100)
        x.append(percent)
        y.append(pitch_to_freq(pitches[n][0]))

    smooth_x = []
    smooth_y = []
    for i, n in enumerate(x):
        smooth_x.append(n)
        smooth_y.append(y[i])
        if i > 0 and i + 1 < len(x):
            smooth_x.append(n+1)
            smooth_y.append(y[i+1])

    print(x, y)
    print(smooth_x, smooth_y)

    p = phoneme_nodes[vowel_offset]
    p.attrib["d"] = str(vowel_duration)
    p.attrib["f0"] = get_f0(smooth_x, smooth_y)

    if pos == 0:
        margin[1] = 0
    elif pos == -1:
        margin[0] = 0
    else:
        margin = [0, 0]

    return node, margin


def generate_word_node(node, rhythms, pitches):
    pass


def assign_bar_to_sentence(num_syl, bars):
    cnt = 0
    i = None
    for i in range(len(bars)):
        cnt += len(bars[i])
        if cnt > num_syl:
            break
    return i+1, cnt


# left to right allocation
def allocate_notes(root, bars, rhythms, pitches):
    nodes = []
    bar_offset = 0
    beat_offset = 0
    cur_time = 0

    syl_offset = 0
    word_nodes = root.findall(".//{http://mary.dfki.de/2002/MaryXML}t")
    num_words = len(word_nodes)
    # number of syllables in the sentence
    num_syl = len(root.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable"))
    # number of bars the sentence will be allocated to
    num_bars = math.ceil(num_syl / 4.0)
    # lower bound number of syllables within one bar
    min_syl_per_bar = math.floor(num_syl / num_bars)
    # the offset of the syllable in the bar
    assigned_bars, num_notes = assign_bar_to_sentence(num_syl, bars)
    margin = [0, 0]

    for i, w_node in enumerate(word_nodes):
        # allocating notes for a word
        is_end_word = (i + 1 == num_words)  # True if this is the last word in the sentence
        note_offset = bars[bar_offset][beat_offset][0]
        # insert silent node before a word
        prefix = rhythms[note_offset][0] - cur_time
        # prefix -= margin[1]  # trim the margin of the last word
        margin = [0, 0]

        syl_nodes = w_node.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")

        for j, s_node in enumerate(syl_nodes):
            notes = []
            pos = 1
            if j + 1 == len(syl_nodes):  # this is the last syllable
                pos = -1
                if is_end_word:  # this is the last syllable of the last word
                    print("last word", i, j, bar_offset, beat_offset)
                    for k in bars[bar_offset][beat_offset:]:
                        notes += k
                else:
                    syl_next_word = word_nodes[i+1].findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")
                    if len(syl_next_word) < (len(bars[bar_offset]) - beat_offset):
                        # there is enough room for all the syllables in the next word
                        notes = bars[bar_offset][beat_offset]
                        print("last syllable next", i, j, len(syl_next_word), beat_offset, bar_offset, bars[bar_offset])
                    else:
                        # there is no room for the next syllable
                        # consume the rest beats and switch to the next bar
                        print("last syllable no next", i, j, bar_offset, beat_offset)
                        for k in bars[bar_offset][beat_offset:]:
                            notes += k
                        beat_offset = -1
                        bar_offset += 1
            else:  # not the last syllable of the word
                if j == 0:
                    pos = 0
                print("default", i, j, bar_offset, beat_offset)
                notes = bars[bar_offset][beat_offset]

            new_node, new_margin = generate_syllable_node(s_node, notes, rhythms, pitches, pos)
            margin[0] += new_margin[0]
            margin[1] += new_margin[1]
            beat_offset += 1
            cur_time = rhythms[notes[-1]][0] + rhythms[notes[-1]][1]

        # prefix -= margin[0]  # trim the margin of the current word
        # if prefix > 0:
        nodes.append(generate_silent_node(prefix))
        nodes.append(w_node)

    wraper_node = root.find(".//{http://mary.dfki.de/2002/MaryXML}phrase")
    wraper_node.clear()
    for i, n in enumerate(nodes):
        wraper_node.insert(i, n)


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
