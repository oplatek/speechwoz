from streamlit_webrtc import (
    webrtc_streamer,
    WebRtcMode,
    WebRtcStreamerContext,
)
from aiortc.contrib.media import MediaRecorder
from pathlib import Path
import os
from collections import defaultdict
import logging
import string
import random
import numpy as np
import json
import argparse
import streamlit as st
from datetime import datetime
from lhotse import MonoCut, Recording, CutSet, SupervisionSegment
from lhotse.utils import fastcopy


MEDIA_STREAM_CONSTRAINTS = {
    "video": False,
    "audio": {
        # these setting doesn't work
        # "sampleRate": 48000,
        # "sampleSize": 16,
        # "channelCount": 1,
        "echoCancellation": False,  # don't turn on else it would reduce wav quality
        "noiseSuppression": True,
        "autoGainControl": True,
    },
}


def get(key, value=None):
    return st.session_state.get(key, value)


def wavpath():
    return f"{get('outdir')}/{get('recording_id')}.wav"


def ins(key, value):
    st.session_state[key] = value


def ins_once(key, value):
    if key not in st.session_state:
        ins(key, value)


def aiortc_audio_recorder():
    def recorder_factory():
        logging.warning("Saving {wavpath()}")
        return MediaRecorder(wavpath(), format="wav")

    webrtc_streamer(
        key="webrtc_streamer",
        audio_receiver_size=4,
        # audio_receiver_size=256,
        sendback_audio=False,
        # mode=WebRtcMode.SENDONLY,
        mode=WebRtcMode.SENDRECV,
        in_recorder_factory=recorder_factory,
        media_stream_constraints=MEDIA_STREAM_CONSTRAINTS,
    )


def initialize():
    st.set_page_config(
        page_title="Dialog evaluation",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={},
    )


def conversation_len(i):
    return len(get("conversations")[i]["turns"])


def get_cut():
    pid = get("participant_id")
    cid = get("conv_id", None)
    tid = get("turn_id", None)
    segment = get("segment")
    ss = get("segment_start")
    cs = get("conversation_start")
    start = (ss - cs).total_seconds()
    duration = (datetime.now() - ss).total_seconds()
    if cid is not None:
        current_turn = get("conversations")[cid]["turns"][tid]
        mw_text = current_turn["utterance"]
        mw_speaker = current_turn["speaker"]
    i = f"{pid}-{cid}-{tid}-{segment}"
    sup = SupervisionSegment(
        id=i,
        channel=0,
        recording_id=get("recording_id"),
        start=start,
        duration=duration,
        text=mw_text,
        speaker=pid,
        custom={
            "multiwoz": {
                "speaker": mw_speaker,
                "conversation_id": cid,
                "prompt": mw_text,
                "turn_id": tid,
            }
        },
    )
    c = MonoCut(id=i, start=start, duration=duration, channel=0, supervisions=[sup])
    return c


def set_prolific_pid():
    params = st.experimental_get_query_params()
    ins_once(
        "participant_id",
        params.get(
            "PROLIFIC_PID",
            [
                "".join(
                    random.choice(string.ascii_lowercase + string.digits)
                    for i in range(8)
                )
            ],
        )[0],
    )


def get_cutset(sex, age, lang):
    prolific_custom = {
        "speaker": {
            "prolificPID": get("participant_id"),
            "sex": sex,
            "age": age,
            "lang": lang,
        }
    }
    r = Recording.from_file(wavpath())
    logging.warning(f"Cuts: {get('cuts')}")
    cuts = dict(
        [
            (
                c.id,
                fastcopy(
                    c,
                    recording=r,
                    supervisions=[
                        fastcopy(
                            c.supervisions[0],
                            # Merge dictionaries
                            custom={
                                **c.supervisions[0].custom,
                                **prolific_custom,
                            },
                        )
                    ],
                ),
            )
            for c in get("cuts")
        ]
    )
    cs = CutSet(cuts=cuts)
    return cs


@st.cache(suppress_st_warning=True)
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--inputs",
        type=str,
        required=True,
        help="A json file containing MultiWOZ_2.2. data (JSON).",
    )
    parser.add_argument(
        "-p",
        "--prolific_token",
        type=str,
        required=True,
        help="prolific token so the people can",
    )
    parser.add_argument(
        "-s",
        "--summary",
        type=str,
        required=True,
        help="A json file containing MultiWOZ_2.1 data for goal summary",
    )
    parser.add_argument(
        "-c",
        "--conv-ids",
        default=None,
        type=str,
        help="Comma separated list of conversation ids to use",
    )
    parser.add_argument(
        "--max-convs",
        type=int,
        default=1,
        help="Maximal number of conversations shown to the participant.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=7,
        help="Soft upper bound for the number of dialog turns (in total) shown to the participant.",
    )
    parser.add_argument(
        "-n",
        "--name",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--outdir",
        type=str,
        default=".",
    )
    return parser.parse_args()


@st.cache(allow_output_mutation=True)
def load_data(args):
    with open(args.inputs, "rt") as r:
        m22 = json.load(r)
    with open(args.summary, "rt") as r:
        m21 = json.load(r)

    m22 = dict([(d["dialogue_id"], d) for d in m22])
    conv_ids = args.conv_ids.split(",") if args.conv_ids else list(m22.keys())

    assert set(conv_ids).issubset(set(m21.keys()))
    assert set(conv_ids).issubset(set(m22.keys()))
    conversations = {}
    for cid in conv_ids:

        # TODO extract dialogue_act for system from m21 data for system turns
        # TODO extract summary from m21 data for user turns
        # TODO extract services / domains from m22 data per dialogue
        c = {
            "dialogue_id": cid,
            "turns": [
                {
                    "speaker": t["speaker"],
                    "turn_id": t["turn_id"],
                    "utterance": t["utterance"],
                }
                for t in m22[cid]["turns"]
            ],
        }
        conversations[cid] = c

    return conversations


def display_form():
    with st.form(key="feedback-form"):
        lang = st.text_input("Your native language(s)")
        age = st.text_input("Age")
        sex_default = "female / male"
        sex = st.text_input("Sex", sex_default)
        note = st.text_area("Leave us feedback:")
        warning_placeholder = st.empty()
        form = st.form_submit_button("Submit feedback")

    questionnaire_filled = len(lang) > 0 and len(age) > 0 and sex != sex_default

    if form:
        if not questionnaire_filled:
            warning_placeholder.error("You have to fill the form first!")
        else:
            st.title("Thank you!")
            st.balloons()

            cs = get_cutset(sex, age, lang)
            cs.to_file(get("outdir") / f"{get('participant_id')}.jsonl.gz")
            if len(note) > 0:
                with open(f"feedback_{get('participant_id')}.txt", "wt") as w:
                    w.write(note)

            st.success("Thank you! Your are finished! Click below.")
            st.markdown(
                f"[Complete the study on prolific!](https://app.prolific.co/submissions/complete?cc={get('prolific_token')})"  # noqa
            )
            return True
    return False


def display_conversation():
    #
    # Assumes Python 3.7+ and stable keys sort
    ins("conv_id", list(get("conversations"))[get("conv_id_idx")])

    turns = get("conversations")[get("conv_id")]["turns"]
    turns2display = turns[: max(get("turn_id"), 0)]
    current_turn = turns[get("turn_id")]

    # if not st.session_state["webrtc_ctx"].state.playing:
    #     st.warning("Waiting for recording to start")
    #     return

    ins("conversation_start", datetime.now())
    if get("turn_id") == -1:
        ins("segment", "coffee")
    ins("segment_start", get("conversation_start"))

    info_break = st.empty()

    # navigation
    def start_turn():
        # end of previous segment
        get("cuts").append(get_cut())  # save
        logging.warning(f"Cuts: {len(get('cuts'))}")
        info_break = st.empty()
        speaker = "CLIENT" if current_turn["speaker"] == "USER" else "AGENT"
        ins("segment_start", datetime.now())
        ins("segment", speaker)

        get("recordings")[get("conv_id")][get("turn_id")] = 1

        if get("turn_id") < len(turns) - 1:
            # before end of conversation
            ins("turn_id", get("turn_id") + 1)
            logging.warning(
                f"conv: {get('conv_id')}, turn: {get('turn_id')}, {get('recordings')}"
            )
        else:
            # end of conversation
            ins("segment", "coffee")
            if get("conv_id_idx") == len(get("conversations")) - 1:
                # All unselected -> All conversations done -> Finish
                # st.balloons()
                # st.title(
                #     "Please stop the recording and fill the survey and you are finished!"
                # )
                pass
            else:
                ins("conv_id_idx", get("conv_id_idx") + 1)
                ins("turn_id", 0)
                logging.warning(
                    f"New conv conv: {get('conv_id')}, turn: {get('turn_id')}"
                )

    def coffee_break():
        # end of previous segment
        get("cuts").append(get_cut())
        logging.warning(f"Cuts: {len(get('cuts'))}")
        # new segment
        ins("segment_start", datetime.now())
        ins("segment", "coffee")
        info_break = st.warning("Enjoy your coffee break - You are not acting")

    with st.form(key="turn_navigation_form"):
        left, right = st.columns([20, 20])
        speaker = "CLIENT" if current_turn["speaker"] == "USER" else "AGENT"
        left.form_submit_button(f"⏺ Next '{speaker}' prompt", on_click=start_turn)
        # right.form_submit_button("Coffee break ", on_click=coffee_break)

    # ## recording

    # ### display current turn
    # greyer colours in past turns
    if get("segment") == "AGENT":
        st.info(f"{current_turn['utterance']}")
    elif get("segment") == "CLIENT":
        st.warning(f"{current_turn['utterance']}")
    else:
        assert get("segment") == "coffee", f"{get('segment')}"
        st.error("Please click above to get your prompt!")

    st.subheader("🗨️ &nbsp; Past dialog utterances:")
    st.progress((get("turn_id") + 1) / (conversation_len(get("conv_id"))))

    # past turns
    for turn in reversed(turns2display):
        if turn["turn_id"] == get("turn_id"):
            # Stop before actual turn
            break
        if turn["speaker"] == "USER":
            st.info(f"{turn['utterance']}")
        else:
            st.warning(f"{turn['utterance']}")
    else:
        st.markdown(
            "**➼➼➼➼➼➼ A NEW CONVERSATION ** ...   _The prompts you record appear here._"
        )


def prepare_data(args):
    if "conversations" in st.session_state:
        return

    with st.spinner("Loading data, please wait ..."):
        conversations = load_data(args)

        eval_converasations = {}
        for i, c in conversations.items():
            if len(eval_converasations) >= args.max_convs:
                break
            if len(c["turns"]) > args.max_turns:
                logging.warning(f"Filtering out too long conversation: {i}")
                continue
            eval_converasations[i] = c

    ins("conversations", eval_converasations)
    ins("prolific_token", args.prolific_token)


def run_application(args):

    #
    # Side bar & submitting

    css = """
        .stRadio > div > label:first-of-type {
            display: none
        }

        [data-testid="stSidebar"] .stButton {
            width: 100% !important;
        }

        .stButton > button {
            height: 50px;
            padding: 0 20px;
        }

        [data-testid="stSidebar"] .stButton > button {
            width: 100% !important;
        }

        [data-testid="stSidebar"] > div:first-of-type {
            padding-top: 1.5rem;
        }

        .main > div {
            padding-top: 1.0rem;
        }

        .stProgress div {
            height: 0.3rem
        }

        .stAlert > [data-baseweb="notification"] {
            padding: 0.25rem 0.45rem;
            margin-bottom: -0.4rem;
        }

        #your-response-ranking {
            margin-top: 1.25rem;
        }

        #past-dialog-utterances {
            margin-top: 0.0rem;
        }

        [data-testid="stHorizontalBlock"] > [data-testid="stBlock"] [data-testid="stBlock"] {
            border: solid 1px rgb(70,70,70);
            border-radius: 5px;
            padding: 0.4rem 0.6rem 0.7rem 0.6rem;
        }

    """
    ins_once("recordings", defaultdict(dict))
    ins_once("turn_id", -1)
    ins_once("conv_id_idx", 0)

    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)

    st.sidebar.markdown("### _Conversation recording progress_")

    set_prolific_pid()
    ins_once("outdir", Path(args.outdir) / args.name)
    os.makedirs(get("outdir"), exist_ok=True)
    recording_id = get(
        "participant_id"
    )  # + datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    ins_once("recording_id", recording_id)
    ins_once("cuts", [])

    aiortc_audio_recorder()  # first way

    progress_msgs = []
    completed_all = []
    for i, cid in enumerate(get("conversations")):
        completed = sum(get("recordings")[cid].values())
        total = conversation_len(cid)
        completed_all.append(completed >= total)
        progress_msgs.append(
            f"{i + 1}. Conversation {i+1} ({completed}/{total} completed)"
        )
    st.sidebar.markdown("\n".join(progress_msgs))

    st.sidebar.title("Instructions")
    st.sidebar.markdown(
        """
    1. ### Read the prompt precisely
    2. ### Act as un client or call center agent
    3. ### Do not stop the recording before you record all the conversations
    """
    )

    if not get("webrtc_streamer").state.playing and not all(completed_all):
        st.error("Start the recording by clicking above on the Start button")
    else:
        if not all(completed_all):
            display_conversation()
        else:
            if get("webrtc_streamer").state.playing:
                st.error("Stop the recording before you fill the final form")
            else:
                done = display_form()
                if done:
                    return


if __name__ == "__main__":
    initialize()
    args = parse_args()
    prepare_data(args)
    run_application(args)
