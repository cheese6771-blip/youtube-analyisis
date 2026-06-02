import re
from collections import Counter

import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt

from wordcloud import WordCloud
from googleapiclient.discovery import build

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="💗",
    layout="wide"
)

st.title("💗 YouTube 댓글 분석 대시보드")
st.markdown("유튜브 링크를 입력하면 댓글을 수집하고 분석합니다.")

# -----------------------------
# API KEY
# -----------------------------
API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# -----------------------------
# KONLPY
# -----------------------------
try:
    from konlpy.tag import Okt

    okt = Okt()

except Exception:
    okt = None


# -----------------------------
# FUNCTIONS
# -----------------------------
def extract_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)"
    ]

    for pattern in patterns:

        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None


def get_comments(video_id, target_count):

    comments = []

    progress_bar = st.progress(0)
    status = st.empty()

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    while request and len(comments) < target_count:

        response = request.execute()

        for item in response["items"]:

            if len(comments) >= target_count:
                break

            comment = item["snippet"]["topLevelComment"]["snippet"]

            comments.append(
                {
                    "comment": comment["textDisplay"],
                    "likeCount": comment["likeCount"],
                    "publishedAt": comment["publishedAt"],
                    "author": comment["authorDisplayName"]
                }
            )

        current = min(len(comments), target_count)

        progress = current / target_count

        progress_bar.progress(progress)

        status.info(
            f"댓글 수집 중... {current:,}/{target_count:,}"
        )

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    progress_bar.empty()
    status.empty()

    return pd.DataFrame(comments)


def extract_keywords(texts):

    text = " ".join(texts)

    if okt:

        words = okt.nouns(text)

        words = [
            w for w in words
            if len(w) >= 2
        ]

    else:

        words = re.findall(r"\w+", text)

    return Counter(words)


# -----------------------------
# INPUT SECTION
# -----------------------------
st.subheader("영상 입력")

url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=..."
)

comment_count = st.slider(
    "수집할 댓글 수",
    min_value=10,
    max_value=5000,
    value=500,
    step=10
)

# -----------------------------
# RUN BUTTON
# -----------------------------
if st.button("🚀 댓글 분석 시작"):

    if not url:
        st.warning("YouTube 링크를 입력하세요.")
        st.stop()

    video_id = extract_video_id(url)

    if not video_id:
        st.error("유효한 YouTube 링크가 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_comments(
            video_id,
            comment_count
        )

    if df.empty:
        st.error("댓글을 가져오지 못했습니다.")
        st.stop()

    st.success(
        f"{len(df):,}개의 댓글 수집 완료!"
    )

    # -----------------------------
    # SUMMARY
    # -----------------------------
    st.subheader("📊 기본 통계")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "댓글 수",
        f"{len(df):,}"
    )

    c2.metric(
        "평균 좋아요",
        round(df["likeCount"].mean(), 2)
    )

    c3.metric(
        "최대 좋아요",
        int(df["likeCount"].max())
    )

    # -----------------------------
    # COMMENT TREND
    # -----------------------------
    st.subheader("📈 댓글 추이")

    df["publishedAt"] = pd.to_datetime(
        df["publishedAt"]
    )

    trend = (
        df
        .set_index("publishedAt")
        .resample("D")
        .size()
        .reset_index(name="comment_count")
    )

    fig = px.line(
        trend,
        x="publishedAt",
        y="comment_count",
        markers=True,
        title="일별 댓글 수",
        color_discrete_sequence=["#FF69B4"]
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # -----------------------------
    # LIKE DISTRIBUTION
    # -----------------------------
    st.subheader("❤️ 좋아요 분포")

    fig2 = px.histogram(
        df,
        x="likeCount",
        nbins=30,
        title="댓글 좋아요 분포",
        color_discrete_sequence=["#FFB6C1"]
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # -----------------------------
    # TOP COMMENTS
    # -----------------------------
    st.subheader("🔥 좋아요 TOP 10 댓글")

    top_comments = (
        df
        .sort_values(
            "likeCount",
            ascending=False
        )
        .head(10)
    )

    st.dataframe(
        top_comments[
            [
                "author",
                "likeCount",
                "comment"
            ]
        ],
        use_container_width=True
    )

    # -----------------------------
    # KEYWORDS
    # -----------------------------
    st.subheader("📝 자주 등장하는 단어")

    counter = extract_keywords(
        df["comment"].tolist()
    )

    top_words = pd.DataFrame(
        counter.most_common(20),
        columns=[
            "word",
            "count"
        ]
    )

    fig3 = px.bar(
        top_words,
        x="word",
        y="count",
        color="count",
        color_continuous_scale="RdPu",
        title="TOP 20 키워드"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # -----------------------------
    # WORD CLOUD
    # -----------------------------
    st.subheader("☁️ 워드클라우드")

    wc = WordCloud(
        width=1200,
        height=600,
        background_color="white",
        colormap="RdPu"
    ).generate_from_frequencies(
        counter
    )

    fig4, ax = plt.subplots(
        figsize=(14, 7)
    )

    ax.imshow(wc)
    ax.axis("off")

    st.pyplot(fig4)

    # -----------------------------
    # DOWNLOAD CSV
    # -----------------------------
    st.subheader("📥 데이터 다운로드")

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "CSV 다운로드",
        csv,
        file_name="youtube_comments.csv",
        mime="text/csv"
    )

    # -----------------------------
    # RAW DATA
    # -----------------------------
    with st.expander("원본 댓글 데이터"):

        st.dataframe(
            df,
            use_container_width=True
        )
