"""퇴근했으니 퇴근 좀 — 실행: streamlit run app.py
GitHub에 app.py와 requirements.txt를 업로드하고 Streamlit Community Cloud에서
app.py를 선택해 배포하세요. API 키나 외부 데이터베이스 없이 실행합니다.
한 기기/브라우저 세션에서 가족이 함께 사용합니다. 다른 접속자와 실시간 공유되지
않으며 새로고침·세션 종료 시 기록이 사라질 수 있습니다. JSON 백업을 사용하세요.
계산은 가족별 순차 작업을 가정한 계획용 추정치이며 실제 휴식을 보장하지 않습니다.
"""
import datetime as dt
import html
import json
import uuid
import streamlit as st

STATES = ('할 일', '진행 중', '완료')
LOADS = ('앉아서 가능', '서서 하는 일', '걷는 일', '무거운 물건 취급')


def minutes_for(tasks, name):
    pending = [t for t in tasks if t['status'] != '완료']
    original = sum(t['minutes'] for t in pending if t['owner'] == name)
    assigned = sum(t['minutes'] for t in pending if t['assignee'] == name)
    transferred = sum(t['minutes'] for t in pending if t['owner'] == name and t['assignee'] != name)
    return original, assigned, transferred


def validate_backup(raw):
    if not isinstance(raw, dict) or raw.get('version') != 1:
        raise ValueError('지원하지 않는 백업 형식입니다.')
    members = raw.get('members')
    tasks = raw.get('tasks')
    if not isinstance(members, list) or not 1 <= len(members) <= 12:
        raise ValueError('가족 구성원은 1~12명이어야 합니다.')
    if any(not isinstance(n, str) or not n.strip() or len(n) > 20 for n in members) or len(set(members)) != len(members):
        raise ValueError('가족 이름을 확인해 주세요.')
    if not isinstance(tasks, list) or len(tasks) > 100:
        raise ValueError('할 일은 최대 100개입니다.')
    ids = set()
    for t in tasks:
        if not isinstance(t, dict):
            raise ValueError('할 일 형식이 올바르지 않습니다.')
        if not isinstance(t.get('id'), str) or not t['id'] or len(t['id']) > 100 or t['id'] in ids:
            raise ValueError('할 일 ID를 확인해 주세요.')
        ids.add(t['id'])
        if not isinstance(t.get('title'), str) or not t['title'].strip() or len(t['title']) > 80:
            raise ValueError('할 일 제목을 확인해 주세요.')
        if type(t.get('minutes')) is not int or not 1 <= t['minutes'] <= 240:
            raise ValueError('예상 시간은 1~240분이어야 합니다.')
        if t.get('owner') not in members or t.get('assignee') not in members or t.get('status') not in STATES or t.get('load') not in LOADS:
            raise ValueError('담당자 또는 작업 상태를 확인해 주세요.')
    return members, [{k:t[k] for k in ('id','title','minutes','owner','assignee','status','load')} for t in tasks]


def task_card(t):
    moved = t['owner'] != t['assignee']
    badge = '도움 약속' if moved else '내 할 일'
    st.markdown(f'''<div class="task"><span class="badge">{badge}</span>
<h3>{html.escape(t['title'])}</h3><p>{t['minutes']}분 · {html.escape(t['load'])}</p>
<p>{html.escape(t['owner'])} → <b>{html.escape(t['assignee'])}</b> · {t['status']}</p></div>''', unsafe_allow_html=True)


def main():
    st.set_page_config(page_title='퇴근했으니 퇴근 좀', page_icon='🛋️', layout='centered')
    st.markdown('''<style>
.stApp{background:#f1f5f3;color:#233f36}.block-container{max-width:850px;padding-top:2.3rem}
h1,h2,h3{color:#233f36}.hero{padding:28px;background:#234e40;color:#fff9ef;border-radius:22px;margin-bottom:20px}
.hero h1{color:#fff9ef;font-size:2.1rem;line-height:1.35}.hero p{color:#d6e7dc;line-height:1.7}
.tag{font-size:12px;letter-spacing:2px}.task{padding:20px 22px;background:#fffefa;border:1px solid #d4dfd7;border-radius:16px;margin-top:12px}
.task h3{font-size:1.15rem;margin:12px 0 6px}.task p{margin:4px 0;font-size:14px;color:#526b60}
.badge{background:#f7dfad;border-radius:6px;padding:4px 8px;color:#534320;font-size:12px}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:#2e6952;border:0}
div[data-testid="stMetric"]{background:#fffefa;padding:15px;border-radius:14px;border:1px solid #d4dfd7}
</style>''', unsafe_allow_html=True)
    if 'members' not in st.session_state:
        st.session_state.members = ['엄마', '아빠', '나']
        st.session_state.tasks = []
    ss = st.session_state
    st.markdown('''<div class="hero"><div class="tag">OUR FAMILY · REST SHIFT</div>
<h1>퇴근했으니<br>퇴근 좀.</h1><p>집에서도 이어지는 할 일.<br>오늘은 하나씩 나눠 맡고, 쉴 틈을 만들어 봐요.</p></div>''', unsafe_allow_html=True)
    st.caption('한 기기에서 함께 사용하는 가족 보드 · 별도 가입/API 키 없음 · 기록은 백업 파일로 보관')
    with st.sidebar:
        st.header('우리 집 설정')
        with st.form('members_form'):
            names = st.text_input('가족 이름을 쉼표로 구분', value=', '.join(ss.members), max_chars=250)
            update = st.form_submit_button('구성원 적용')
        if update:
            members = list(dict.fromkeys(n.strip() for n in names.split(',') if n.strip()))
            if not 1 <= len(members) <= 12 or any(len(n) > 20 for n in members):
                st.error('1~12명, 이름당 20자 이내로 입력해 주세요.')
            elif any(t['owner'] not in members or t['assignee'] not in members for t in ss.tasks):
                st.error('기록에 등장하는 구성원은 삭제할 수 없어요. 해당 일을 삭제하거나 먼저 담당자를 변경하세요.')
            else:
                ss.members = members
                st.rerun()
        st.divider()
        backup = json.dumps({'version':1,'members':ss.members,'tasks':ss.tasks}, ensure_ascii=False, indent=2)
        st.download_button('기록 백업 · JSON', backup, '가족휴식기록.json', 'application/json', use_container_width=True)
        uploaded = st.file_uploader('백업 불러오기', type=['json'])
        replace = st.checkbox('불러오면 현재 목록이 대체되는 것을 확인했어요.')
        if st.button('백업 적용', disabled=not uploaded or not replace):
            try:
                if uploaded.size > 200000:
                    raise ValueError('백업 파일은 200KB 이하로 올려 주세요.')
                members, tasks = validate_backup(json.loads(uploaded.getvalue().decode('utf-8-sig')))
                ss.members, ss.tasks = members, tasks
                st.rerun()
            except (ValueError, UnicodeError, TypeError):
                st.error('백업 형식을 확인해 주세요. 현재 기록은 변경하지 않았어요.')
        st.caption('새로고침·세션 종료 시 데이터가 사라질 수 있어요. 가족 사진이나 건강정보 같은 민감한 내용은 기록하지 마세요.')
        with st.expander('계산 방식과 한계'):
            st.write('미완료 일의 예상 시간을 담당자별로 합산합니다. 각자 일을 하나씩 순서대로 하고, 사람 간 대기나 공용 기구 충돌은 없다고 가정합니다. 진행 중인 일도 입력한 전체 시간을 사용하므로 남은 시간에 맞게 수정하세요.')
            st.write('덜어 준 시간은 완료된 실제 시간이 아니라, 다른 가족이 맡기로 한 미완료 작업 시간입니다. 일을 나눠도 요청·중단 등이 생길 수 있어 실제 연속 휴식은 보장하지 않습니다.')
    overview, add, board = st.tabs(['🛋️ 쉴 틈 확인', '📝 남은 일 적기', '🙋 내가 할게'])
    with add:
        st.subheader('오늘 남은 일을 적어 주세요')
        st.caption('이미 끝낸 부분은 빼고, 앞으로 필요한 시간만 적어요. 한 일의 담당자는 한 명으로 기록됩니다.')
        with st.form('add_task', clear_on_submit=True):
            title = st.text_input('어떤 일인가요?', max_chars=80, placeholder='예: 저녁 설거지')
            a,b = st.columns(2)
            owner = a.selectbox('원래 하려던 가족', ss.members)
            duration = b.number_input('예상 소요 시간(분)', min_value=1, max_value=240, value=15, step=1)
            load = st.selectbox('일의 특징', LOADS)
            if st.form_submit_button('할 일 추가', type='primary', use_container_width=True):
                if not title.strip():
                    st.warning('할 일 이름을 입력해 주세요.')
                elif len(ss.tasks) >= 100:
                    st.warning('최대 100개까지 등록할 수 있어요.')
                else:
                    ss.tasks.append({'id':uuid.uuid4().hex,'title':title.strip(),'minutes':int(duration),'owner':owner,'assignee':owner,'status':'할 일','load':load})
                    st.rerun()
    with board:
        st.subheader('할 수 있는 일 하나만, 내가 할게')
        st.caption('상대가 원하는 도움인지 먼저 물어보세요. 무리한 동작이나 위험한 작업은 맡지 않아요.')
        show_done = st.checkbox('완료한 일도 보기')
        visible = [t for t in ss.tasks if show_done or t['status'] != '완료']
        if not visible:
            st.info('아직 할 일이 없어요. ‘남은 일 적기’에서 등록하거나 완료한 일 보기를 켜 보세요.')
        for t in visible:
            task_card(t)
            with st.form('edit_'+t['id']):
                a,b = st.columns(2)
                who = a.selectbox('이번 담당자', ss.members, index=ss.members.index(t['assignee']), key='who_'+t['id'])
                state = b.selectbox('상태', STATES, index=STATES.index(t['status']), key='state_'+t['id'])
                mins = st.number_input('남은 예상 시간(분) · 완료 시 기록용', 1, 240, value=t['minutes'], key='mins_'+t['id'])
                save = st.form_submit_button('이렇게 맡을게 · 변경 반영', use_container_width=True)
                if save:
                    t.update(assignee=who,status=state,minutes=int(mins))
                    st.rerun()
            with st.expander('이 일 삭제'):
                confirm = st.checkbox('이 기록을 삭제할게요', key='confirm_'+t['id'])
                if st.button('삭제', key='delete_'+t['id'], disabled=not confirm):
                    ss.tasks = [v for v in ss.tasks if v['id'] != t['id']]
                    st.rerun()
    with overview:
        st.subheader('오늘은 누가 쉬었으면 좋겠나요?')
        person = st.selectbox('쉴 틈을 확인할 가족', ss.members)
        start = st.time_input('남은 일을 시작할 기준 시각', value=dt.datetime.now().replace(second=0,microsecond=0).time(), step=300)
        wanted = st.slider('확보하고 싶은 휴식 시간(분)', 5, 120, 30, step=5)
        original, assigned, transferred = minutes_for(ss.tasks, person)
        a,b,c = st.columns(3)
        a.metric('원래 남아 있던 내 일', f'{original}분')
        b.metric('현재 맡은 일', f'{assigned}분')
        c.metric('가족이 대신 맡은 내 일', f'{transferred}분')
        net = original-assigned
        if net > 0:
            st.success(f'현재 계획에서는 {person}의 작업 부담이 {net}분 줄었어요.')
        elif net < 0:
            st.info(f'{person}이 다른 가족의 일을 맡아, 작업 부담이 원래보다 {-net}분 늘었어요.')
        elif ss.tasks:
            st.info('현재 계획에서는 작업 시간의 순변화가 없어요.')
        if not ss.tasks:
            st.info('먼저 오늘 남은 일을 등록해 주세요. 담당을 바꾸면 이 화면의 시간이 바뀝니다.')
        else:
            base = dt.datetime.combine(dt.date.today(), start)
            finish = base+dt.timedelta(minutes=assigned)
            rest_end = finish+dt.timedelta(minutes=wanted)
            def clock(value):
                days=(value.date()-base.date()).days
                return (f'+{days}일 ' if days else '')+value.strftime('%H:%M')
            st.markdown(f'### 예상 휴식 구간 · {clock(finish)} → {clock(rest_end)}')
            st.caption(f'{start.strftime("%H:%M")}부터 현재 맡은 일을 순서대로 끝내고, 이후 다른 일정이 없을 때의 {wanted}분 휴식 후보예요. 확정된 자유 시간은 아닙니다.')
            own = [t for t in ss.tasks if t['assignee'] == person and t['status'] != '완료']
            cursor=base
            if own:
                st.markdown('**현재 담당 기준 예상 순서**')
                for t in own:
                    end=cursor+dt.timedelta(minutes=t['minutes'])
                    st.write(f'{clock(cursor)}–{clock(end)} · {t["title"]} ({t["minutes"]}분)')
                    cursor=end
            else:
                st.write('현재 이 가족에게 남은 작업은 없어요. 휴식 여부를 함께 확인해 보세요.')
            candidates=[t for t in own if t['owner']==person]
            if candidates and len(ss.members)>1:
                st.markdown('**가족에게 부탁해 볼 일**')
                suggestion=min(candidates,key=lambda t:abs(t['minutes']-wanted))
                st.write(f'‘{suggestion["title"]}’을 다른 가족이 맡으면 이 가족의 남은 작업 시간이 {suggestion["minutes"]}분 줄어요.')
                st.caption('시간만 보고 고른 후보예요. 가족의 여유 시간과 동작 부담을 확인한 뒤 ‘내가 할게’ 탭에서 직접 결정하세요.')
            completed=sum(t['status']=='완료' for t in ss.tasks)
            st.caption(f'전체 작업 {len(ss.tasks)}개 · 완료 {completed}개 · 남은 작업 {len(ss.tasks)-completed}개')
    st.divider()
    st.caption('일을 빨리 끝내라는 앱이 아니라, 누군가 혼자 하지 않아도 되게 돕는 앱입니다. 가족끼리 속도를 평가하거나 도움을 강요하지 않아요.')


if __name__ == '__main__':
    main()
