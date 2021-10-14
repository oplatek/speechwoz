from pathlib import Path
from collections import defaultdict
import logging
import string
import random
import numpy as np
import json
import argparse
import time

import streamlit as st


def initialize():
    st.set_page_config(
        page_title="Dialog evaluation",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={},
    )


def start_recording():
    pass


def save_audio(participant_id, conv_id, turn_id):
    pass


def mark_audio_failure(participant_id, conv_id, turn_id):
    # TODO save also the failure audio
    pass


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
        default=4,
        help="Maximal number of conversations shown to the participant.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=20,
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
        default="outputs",
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


def prepare_data(args):
    if "conversations" in st.session_state:
        return

    with st.spinner("Loading data, please wait ..."):
        conversations = load_data(args)

        eval_converasations = {}
        for i, c in conversations.items():
            if len(eval_converasations) > args.max_convs:
                break
            if len(c["turns"]) > args.max_turns:
                logging.warning(f"Filtering out too long conversation: {i}")
                continue
            eval_converasations[i] = c

    st.session_state["conversations"] = eval_converasations


def run_application(args):
    def conversation_len(i):
        return len(st.session_state["conversations"][i]["turns"])

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
    if "recordings" not in st.session_state:
        st.session_state["recordings"] = defaultdict(dict)
    if "turn_id" not in st.session_state:
        st.session_state["turn_id"] = 0

    if "conv_id_idx" not in st.session_state:
        st.session_state["conv_id_idx"] = 0

    if "recording" not in st.session_state:
        st.session_state["recording"] = False

    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)

    st.sidebar.title("Role playing of System and User")

    # create participang_id
    params = st.experimental_get_query_params()
    if "participant_id" not in st.session_state:
        st.session_state["participant_id"] = params.get(
            "PROLIFIC_PID",
            [
                "".join(
                    random.choice(string.ascii_lowercase + string.digits)
                    for i in range(8)
                )
            ],
        )[0]

    progress_msgs = []
    completed_all = []
    for i, conv_id in enumerate(st.session_state["conversations"]):
        completed = sum(st.session_state["recordings"][conv_id].values())
        total = conversation_len(conv_id)
        completed_all.append(completed == total)
        progress_msgs.append(f"Conversation {i+1} ({completed}/{total} completed)")
    st.sidebar.markdown(" ".join(progress_msgs))

    with st.sidebar.form(key="feedback-form"):
        st.text_input("Your native language(s)")
        st.text_input("Age")
        st.text_input("Sex", "female / male")
        note = st.text_area("Leave us feedback:")
        warning_placeholder = st.empty()
        final_submit = st.form_submit_button("Submit feedback")

    submitted = False
    if final_submit:
        submitted = True

        if all(completed_all):

            st.title("Thank you!")
            st.balloons()

            outdir = Path(args.outdir) / args.name
            metadataname = st.session_state["participant_id"] + ".json"

            outdir.mkdir(exist_ok=True)

            with open(outdir / metadataname, "w+") as f:
                json.dump(
                    {"TODO": "Collect audio stats, number of retries"},
                    f,
                    indent=2,
                )

            wait_time = 3
            status_text = st.empty()
            for i in range(wait_time):
                status_text.success(
                    f"You will be redirected to Prolific in {wait_time - i} s!"
                )
                time.sleep(1)
            # TODO redirection to prolific page
            return

    if submitted:
        if any(
            [
                sum(st.session_state["recordings"][cid].values())
                < conversation_len(cid)
                for cid in st.session_state["conversations"]
            ]
        ):
            warning_placeholder.error(
                "You have to record all the conversrations first!"
            )
        warning_placeholder.error("You have to fill in the study first!")

    #
    # Conversation page

    #
    # Turn page

    # Assumes Python 3.7+ and stable keys sort
    conv_id = list(st.session_state["conversations"])[st.session_state["conv_id_idx"]]

    turn_id = st.session_state["turn_id"]
    turns = st.session_state["conversations"][conv_id]["turns"]
    turns2display = turns[:turn_id]
    current_turn = turns[turn_id]

    logging.warning(f"DEBUGA {conv_id}")
    # navigation
    def record_stop():
        if st.session_state["recording"]:
            st.session_state["recording"] = False
            logging.debug("stopping recording")
            save_audio(st.session_state["participant_id"], conv_id, turn_id)
            st.session_state["recordings"][conv_id][turn_id] = 1
            logging.warning(f"DEBUGB {conv_id} ")

            if turn_id < len(turns) - 1:
                # before end of conversation
                st.session_state["turn_id"] += 1
            else:
                # end of conversation
                if (
                    st.session_state["conv_id_idx"]
                    == len(st.session_state["conversations"]) - 1
                ):  # All unselected
                    # All conversations done
                    st.balloons()
                    st.title("Please fill the survey and you are finished!")
                else:
                    st.session_state["conv_id_idx"] += 1

        else:
            st.session_state["recording"] = True
            logging.warning("starting recording")
            # starting recording
            start_recording()

    def discard():
        # TODO BUG discard uses turn_id + 1 turn :-P
        st.session_state["recordings"][conv_id][turn_id] = 0

        mark_audio_failure(st.session_state["participant_id"], conv_id, turn_id)
        st.session_state["recording"] = False

    logging.warning(f"DEBUGC {conv_id} ")
    with st.form(key="turn_navigation_form"):
        left, right = st.columns([20, 20])
        msg_record_stop = (
            f"⏹ Stop recording '{current_turn['speaker']}' prompt"
            if st.session_state["recording"]
            else f"⏺ Record '{current_turn['speaker']}' prompt"
        )
        left.form_submit_button(msg_record_stop, on_click=record_stop)
        right.form_submit_button("🗑 Discard this recording ", on_click=discard)

    ### recording

    #### display current turn
    # greyer colours in past turns
    if current_turn["speaker"] == "USER":
        st.info(f"{current_turn['utterance']}")
    else:
        st.warning(f"{current_turn['utterance']}")

    st.subheader("🗨️ &nbsp; Past dialog utterances:")
    st.progress((turn_id + 1) / (conversation_len(conv_id)))

    # past turns
    for turn in reversed(turns2display):
        # __import__("ipdb").set_trace()
        if turn["turn_id"] == turn_id:
            # Stop before actual turn
            break
        if turn["speaker"] == "USER":
            st.info(f"{turn['utterance']}")
        else:
            st.warning(f"{turn['utterance']}")
    else:
        st.warning(f"A conversation start - the recorded prompts will appear here.")
    logging.warning(f"DEBUGZ {conv_id} ")

    # TODO dialogue history
    # db_results = [
    #     f"{domain}: {len(turn_data.api_result[domain]['results'])}"
    #     for domain in turn_data.api_result
    # ]
    # st.error(f"*Available database entries:* {', '.join(db_results)}")


if __name__ == "__main__":

    initialize()
    args = parse_args()
    prepare_data(args)
    run_application(args)
