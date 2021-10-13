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
    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)

    st.sidebar.title("Role playing")
    button_placeholders = [
        st.sidebar.empty() for i in range(len(st.session_state["conversations"]))
    ]

    with st.sidebar.form(key="feedback-form"):
        note = st.text_area("Leave us a note:")
        warning_placeholder = st.empty()
        final_submit = st.form_submit_button("Submit feedback")

    submitted = False
    if final_submit:

        submitted = True

        if completed:

            st.title("Thank you!")
            st.balloons()

            params = st.experimental_get_query_params()
            participant_id = params.get(
                "PROLIFIC_PID",
                [
                    "".join(
                        random.choice(string.ascii_lowercase + string.digits)
                        for i in range(8)
                    )
                ],
            )[0]

            outdir = Path(args.outdir) / args.name
            metadataname = participant_id + ".json"

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
        warning_placeholder.error("You have to fill in the study first!")

    #
    # Conversation page

    if "recordings" not in st.session_state:
        st.session_state["recordings"] = defaultdict(dict)
    if "turn_id" not in st.session_state:
        st.session_state["turn_id"] = 0

    if "conversation_selected" not in st.session_state:
        st.session_state["conversation_selected"] = [False] * len(
            st.session_state["conversations"]
        )

    def select_conversation():
        st.session_state["conversation_selected"] = [
            getattr(st.session_state, f"selection_{id}")
            for id in st.session_state["conversations"]
        ]
        st.session_state["turn_id"] = 0

    for i, conv_id in enumerate(st.session_state["conversations"]):
        completed = len(st.session_state["recordings"][conv_id].values())
        total = conversation_len(conv_id)
        button_placeholders[i].button(
            f"Conversation {i+1} ({completed}/{total} completed)",
            key=f"selection_{conv_id}",
            on_click=select_conversation,
        )

    #
    # Turn page

    for selected, conv_id in zip(
        st.session_state["conversation_selected"], st.session_state["conversations"]
    ):
        if not selected:
            continue

        turn_id = st.session_state["turn_id"]

        st.subheader("🗨️ &nbsp; Past dialog utterances:")
        st.progress((turn_id + 1) / (conversation_len(conv_id)))

        turns = st.session_state["conversations"][conv_id]["turns"]

        # past turns
        for turn in turns:
            if turn["turn_id"] == turn_id:
                # Stop before actual turn
                break
            if turn["speaker"] == "USER":
                st.info(f"*USR:* {turn['utterance']}")
            else:
                st.warning(f"*SYS:* {turn['utterance']}")

        # TODO dialogue history
        # db_results = [
        #     f"{domain}: {len(turn_data.api_result[domain]['results'])}"
        #     for domain in turn_data.api_result
        # ]
        # st.error(f"*Available database entries:* {', '.join(db_results)}")

        current_turn = turns[turn_id]

        st.subheader(f"🏆 &nbsp; Record the {current_turn['speaker']} reply:")

        def prev_turn():
            if turn_id > 0:
                st.session_state["turn_id"] -= 1

        def next_turn():
            if turn_id < conversation_len(conv_id) - 1:
                st.session_state["turn_id"] += 1
            # TODO some checks

        with st.form(key="my_form"):

            left, right, _ = st.columns([8, 8, 53])
            left.form_submit_button("« previous turn", on_click=prev_turn)
            right.form_submit_button(
                "Submit"
                if turn_id == conversation_len(conv_id) - 1
                else "Submit & next »",
                on_click=next_turn,
            )


if __name__ == "__main__":

    initialize()
    args = parse_args()
    prepare_data(args)
    run_application(args)
