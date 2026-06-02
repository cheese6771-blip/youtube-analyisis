import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import re
import os

# ------------------
# 페이지 설정
# ------------------

st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="💗",
    layout="wide"
)

# ------------------
# 연분홍 UI
# ------------------

st.markdown("""
<style>
.stApp {
    background-color: #fff5f7;
}

h1, h2, h3 {
    color: #e75480;
}

.stButton > button {
    background-color: #ffb6c1;
    color: black;
    border-radius: 10px;
}

div[data-baseweb="slider"] span {
    background-color: #ff69b4 !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------
# API 설정
# ------------------

API_KEY = st.secrets.get("YOUTUBE_API_KEY")

if not API_KEY:
    st.error("""
    YouTube API 키가 설정되지 않았습니다.

    Streamlit Cloud → Settings → Secrets

    YOUTUBE_API_KEY="YOUR_API_KEY"
    """)
    st.stop()

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# ------------------
# 함수
# ------------------

def extract_video_id(url):

    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]

    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)

    return query.get("v", [None])[0]


def get_comments(video_id, max_comments):

    comments = []
    next_page = None

    try:

        while len(comments) < max_comments:

            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page,
                textFormat="plainText"
            )

            response = request.execute()

            for item in response["items"]:

                comment = item["snippet"]["topLevelComment"]["snippet"]

                comments.append({
                    "text": comment["textDisplay"],
                    "likes": comment["likeCount"],
                    "time": comment["publishedAt"]
                })

                if len(comments) >= max_comments:
                    break

            next_page = response.get("nextPageToken")

            if not next_page:
                break

    except Exception as e:
        st.error(f"댓글 수집 오류: {e}")

    return pd.DataFrame(comments)


def extract_keywords(texts):

    words = []

    for text in texts:

        text = str(text)

        extracted = re.findall(r"[가-힣]{2,}", text)

        words.extend(extracted)

    return Counter(words)

# ------------------
# UI
# ------------------

st.title("💗 YouTube 댓글 분석기")

video_url = st.text_input(
    "유튜브 영상 링크 입력"
)

comment_count = st.slider(
    "수집할 댓글 수",
    min_value=10,
    max_value=5000,
    value=500,
    step=10
)

if st.button("댓글 분석 시작"):

    if not video_url:

        st.warning("유튜브 링크를 입력해주세요.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        video_id = extract_video_id(video_url)

        if not video_id:
            st.error("유효한 유튜브 링크가 아닙니다.")
            st.stop()

        df = get_comments(video_id, comment_count)

    if df.empty:

        st.error("댓글을 가져오지 못했습니다.")
        st.stop()

    st.success(f"{len(df)}개의 댓글을 수집했습니다!")

    # ------------------
    # 댓글 미리보기
    # ------------------

    st.header("💬 댓글 미리보기")

    st.dataframe(df.head())

    # ------------------
    # 시간대 분석
    # ------------------

    st.header("📈 시간대별 댓글 추이")

    df["time"] = pd.to_datetime(df["time"])
    df["hour"] = df["time"].dt.hour

    hour_count = (
        df.groupby("hour")
        .size()
        .reset_index(name="count")
    )

    fig = px.line(
        hour_count,
        x="hour",
        y="count",
        markers=True,
        title="시간대별 댓글 수"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ------------------
    # 좋아요 분석
    # ------------------

    st.header("❤️ 좋아요 분석")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "평균 좋아요",
        round(df["likes"].mean(), 2)
    )

    col2.metric(
        "최대 좋아요",
        int(df["likes"].max())
    )

    col3.metric(
        "총 좋아요",
        int(df["likes"].sum())
    )

    fig2 = px.histogram(
        df,
        x="likes",
        nbins=30,
        title="좋아요 분포"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # ------------------
    # 단어 분석
    # ------------------

    st.header("🔍 자주 등장하는 단어")

    counter = extract_keywords(df["text"])

    top_words = pd.DataFrame(
        counter.most_common(20),
        columns=["단어", "빈도"]
    )

    st.dataframe(top_words)

    fig3 = px.bar(
        top_words,
        x="단어",
        y="빈도",
        title="TOP 20 키워드"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # ------------------
    # 워드클라우드
    # ------------------

    st.header("☁️ 워드클라우드")

    try:

        if not os.path.exists("NanumGothic.ttf"):
            st.error(
                "NanumGothic.ttf 파일을 프로젝트 루트에 업로드해주세요."
            )

        else:

            wc = WordCloud(
                width=1400,
                height=700,
                background_color="white",
                font_path="NanumGothic.ttf"
            )

            wc.generate_from_frequencies(counter)

            fig4, ax = plt.subplots(
                figsize=(14, 7)
            )

            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")

            st.pyplot(fig4)

    except Exception as e:

        st.error(
            f"워드클라우드 생성 오류: {e}"
        )

    # ------------------
    # 전체 댓글
    # ------------------

    st.header("📄 전체 댓글 데이터")

    st.dataframe(df)
