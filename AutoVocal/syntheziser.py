from AutoVocal.maryclient_http import maryclient
from xml.etree import ElementTree as ET
import mido
import mido.messages
import requests
from AutoVocal.syllable import Syllable
import math

VOWELS = "A{6QE@3IO29&U}VY=~"


def generate_song():
    client = maryclient()
    client.set_audio("WAVE_FILE")
    texts = "happy birthday to you, happy birthday to you, happy birthday dear baby, happy birthday to you".split(",")
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
                rhythms.append((cur_time, real_time))
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


def generate_syllable_node(node, notes, rhythms, pitches):
    consonant_duration = 0
    vowel_offset = None
    durations = []
    note_offset = 0

    phoneme_nodes = node.findall(".//{http://mary.dfki.de/2002/MaryXML}ph")
    for i, p in enumerate(phoneme_nodes):
        phoneme_duration = int(p.attrib["d"])
        for ch in p.attrib["p"]:
            if ch.upper() in VOWELS.upper():
                phoneme_duration *= 0
                vowel_offset = i
        durations.append(phoneme_duration)
        consonant_duration += phoneme_duration

    # vowel_duration = duration - consonant_duration
    # durations[vowel_offset] = vowel_duration
    new_phoneme_nodes = []
    for j, p in enumerate(phoneme_nodes):
        # consonant before vowel
        if j < vowel_offset:
            f0 = pitch_to_freq(pitches[notes[0]][0])  # the pitch of the first syllable
            p.attrib["d"] = str(durations[j])
            p.attrib["f0"] = "(1,%s)(100,%s)" % (f0, f0)
        # vowel
        elif j == vowel_offset:
            f0 = pitch_to_freq(pitches[notes[0]][0])  # the pitch of the first syllable
            p.attrib["d"] = str(rhythms[notes[0]][1])
            p.attrib["f0"] = "(1,%s)(100,%s)" % (f0, f0)
            for k, n in enumerate(notes[1:]):
                p_node = generate_phoneme_node(rhythms[n][1], pitches[n])
                new_phoneme_nodes.append((vowel_offset + k + 1, p_node))
        # consonant after vowel
        else:
            f0 = pitch_to_freq(pitches[notes[-1]][0])  # the pitch of the last syllable
            p.attrib["d"] = str(durations[j])
            p.attrib["f0"] = "(1,%s)(100,%s)" % (f0, f0)
    for n in new_phoneme_nodes:
        node.insert(n[0], n[1])

    return node


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
    syl_offset_bar = 0

    for i, w_node in enumerate(word_nodes):
        end = (i == num_words)  # True if this is the last word in the sentence
        note_offset = bars[bar_offset][beat_offset][0]
        # insert silent node before a word
        prefix = rhythms[note_offset][0] - cur_time
        if prefix > 0:
            nodes.append(generate_silent_node(prefix))
        syl_nodes = w_node.findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")

        for j, s_node in enumerate(syl_nodes):
            notes = []
            if beat_offset < min_syl_per_bar - 1:
                print(1, i, j)
                notes = bars[bar_offset][beat_offset]
            else:
                if len(syl_nodes) - 1 > j:  # this is not the last syllable of current word
                    print(2, i, j)
                    notes = bars[bar_offset][beat_offset]
                else:  # the last syllable of current word
                    if end:  # this is the last word
                        print(3, i, j)
                        for k in bars[bar_offset][beat_offset:]:
                            notes += k
                    else:
                        # there is enough room for all the syllables in the next word
                        syl_next_word = word_nodes[i+1].findall(".//{http://mary.dfki.de/2002/MaryXML}syllable")
                        if len(syl_next_word) < (len(bars[bar_offset]) - beat_offset):
                            notes = bars[bar_offset][beat_offset]
                            print(4, i, j, len(syl_next_word), beat_offset, bar_offset, bars[bar_offset])
                        else:
                            print(5, i, j)
                            for k in bars[bar_offset][beat_offset:]:
                                notes += k
                            beat_offset = -1
                            bar_offset += 1
            generate_syllable_node(s_node, notes, rhythms, pitches)
            beat_offset += 1
            cur_time = rhythms[notes[-1]][0] + rhythms[notes[-1]][1]
        nodes.append(w_node)

    wraper_node = root.find(".//{http://mary.dfki.de/2002/MaryXML}phrase")
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
