const MASCOT=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 220" fill="none" role="img" aria-label="Линни, маскот Lingua 360">
  <ellipse cx="100" cy="210" rx="50" ry="8" fill="#0b2d52" opacity=".16"/>
  <ellipse cx="76" cy="198" rx="15" ry="8" fill="#e07a1f"/>
  <ellipse cx="124" cy="198" rx="15" ry="8" fill="#e07a1f"/>
  <ellipse cx="100" cy="134" rx="64" ry="72" fill="#0b2d52"/>
  <path class="mascot-wing mascot-wing-l" d="M40 120c-20 14-26 40-14 58 2-18 16-38 32-50-6-4-12-6-18-8z" fill="#114c86"/>
  <path class="mascot-wing mascot-wing-r" d="M160 120c20 14 26 40 14 58-2-18-16-38-32-50 6-4 12-6 18-8z" fill="#114c86"/>
  <ellipse cx="100" cy="150" rx="40" ry="44" fill="#f4f8fc"/>
  <circle cx="100" cy="76" r="56" fill="#114c86"/>
  <path d="M68 28c8-20 22-26 26-8-10 2-20 8-26 8z" fill="#0b2d52"/>
  <path d="M132 28c-8-20-22-26-26-8 10 2 20 8 26 8z" fill="#0b2d52"/>
  <circle cx="78" cy="78" r="19" fill="#fff"/>
  <circle cx="122" cy="78" r="19" fill="#fff"/>
  <g class="mascot-pupils">
    <circle cx="80" cy="81" r="8.5" fill="#0b2d52"/>
    <circle cx="124" cy="81" r="8.5" fill="#0b2d52"/>
    <circle cx="83" cy="78" r="2.6" fill="#fff"/>
    <circle cx="127" cy="78" r="2.6" fill="#fff"/>
  </g>
  <g class="mascot-lids" fill="#114c86">
    <rect class="mascot-lid" x="59" y="59" width="38" height="18" rx="9"/>
    <rect class="mascot-lid" x="103" y="59" width="38" height="18" rx="9"/>
  </g>
  <circle cx="78" cy="78" r="22" stroke="#f38b2a" stroke-width="4.5"/>
  <circle cx="122" cy="78" r="22" stroke="#f38b2a" stroke-width="4.5"/>
  <path d="M100 70v2" stroke="#f38b2a" stroke-width="5" stroke-linecap="round"/>
  <path class="mascot-beak" d="M91 94l9 16 9-16H91z" fill="#f38b2a"/>
  <ellipse class="mascot-beak-open" cx="100" cy="106" rx="9" ry="7" fill="#b85a14"/>
  <circle cx="100" cy="152" r="18" fill="#f38b2a"/>
  <text x="100" y="158" text-anchor="middle" font-size="12" font-family="Segoe UI, Arial, sans-serif" font-weight="800" fill="#fff">360</text>
</svg>`;
const state={token:localStorage.getItem('lingua_token'),language:'English',dashboard:null,currentLesson:null,blob:null};
const $=s=>document.querySelector(s);const $$=s=>document.querySelectorAll(s);
const escapeHtml=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
function mascotHTML(mood='idle', size='md'){return `<span class="mascot mascot-${size} mood-${mood}">${MASCOT}</span>`}
function setMascotMood(el, mood){if(!el)return;el.classList.remove('mood-idle','mood-talk','mood-listen','mood-happy');el.classList.add('mascot','mood-'+mood)}
function hydrateMascots(root=document){root.querySelectorAll('[data-mascot]').forEach(el=>{const size=el.dataset.mascotSize||'md';const mood=el.dataset.mascot||'idle';el.classList.add('mascot','mascot-'+size,'mood-'+mood);el.innerHTML=MASCOT})}
function tutorRow(inner, mood='idle'){return `<div class="message-row">${mascotHTML(mood,'sm')}<div class="message tutor">${inner}</div></div>`}

async function api(path,options={}){
  const headers={...(options.headers||{})};
  if(state.token)headers.Authorization=`Bearer ${state.token}`;
  if(options.json){headers['Content-Type']='application/json';options.body=JSON.stringify(options.json)}
  const response=await fetch(path,{...options,headers});
  if(!response.ok){const error=await response.json().catch(()=>({detail:'Ошибка сервера'}));throw new Error(error.detail||'Ошибка')}
  return response.json();
}

function showApp(){
  $('#loginView').classList.add('hidden');$('#appView').classList.remove('hidden');
  hydrateMascots($('#appView'));
  if(!$('#chatMessages').children.length)$('#chatMessages').innerHTML=tutorRow('<b>Линни</b><p>Выберите язык и задайте вопрос. Например: «Как произносить TH?»</p>','idle');
  loadDashboard();loadIntegrations();loadVideos();loadReviews();
}
function showLogin(){$('#appView').classList.add('hidden');$('#loginView').classList.remove('hidden')}

$('#loginForm').addEventListener('submit',async event=>{
  event.preventDefault();$('#loginError').textContent='';
  try{const data=await api('/api/auth/login',{method:'POST',json:{email:$('#email').value,password:$('#password').value}});state.token=data.token;localStorage.setItem('lingua_token',data.token);showApp()}
  catch(error){$('#loginError').textContent=error.message}
});
$('#logout').onclick=()=>{state.token=null;localStorage.removeItem('lingua_token');showLogin()};

function showView(view){
  $$('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.view===view));
  $$('.panel-view').forEach(item=>item.classList.add('hidden'));$('#'+view).classList.remove('hidden');
  if(view==='reviews')loadReviews();
}
$$('.nav-item').forEach(button=>button.onclick=()=>showView(button.dataset.view));

async function loadDashboard(){
  try{
    const data=await api('/api/dashboard');state.dashboard=data;
    const en=data.progress.find(item=>item.language==='English');
    const es=data.progress.find(item=>item.language==='Spanish');
    $('#stats').innerHTML=`<div class="stat"><b>${en?.lessons||0}</b><span>уроков English</span></div><div class="stat"><b>${es?.lessons||0}</b><span>уроков Español</span></div><div class="stat"><b>${(en?.xp||0)+(es?.xp||0)}</b><span>XP заработано</span></div><div class="stat"><b>${data.errors}</b><span>тем на повторение</span></div>`;
    $('#enBar').style.width=Math.min(100,5+(en?.xp||0)/10)+'%';$('#esBar').style.width=Math.min(100,5+(es?.xp||0)/10)+'%';
    $('#progressCards').innerHTML=data.progress.map(item=>`<div class="progress-card"><p class="eyebrow">${item.language}</p><div class="big">${item.level}</div><p>${item.lessons} уроков • ${item.minutes} минут • ${item.xp} XP</p></div>`).join('');
    renderSkills(data.skills);
    $('#weekPlan').innerHTML=data.week.slice(0,5).map(item=>`<div class="week-day ${item.language==='Spanish'?'es':''}"><small>${item.day.slice(0,2)}</small><b>${item.language==='English'?'EN':'ES'}</b><span>${item.minutes} мин</span></div>`).join('');
    const day=new Date().getDay();const plannedLanguage=[null,'English','English','Spanish','Spanish','English',null][day]||'English';
    const next=data.plan[plannedLanguage];
    $('#todayLessonTitle').textContent=`${plannedLanguage}: ${next.title}`;$('#todayLessonObjective').textContent=next.objective;
    $('#startToday').onclick=()=>openLesson(plannedLanguage);
  }catch{showLogin()}
}

function renderSkills(skills){
  $('#skillProgress').innerHTML=['English','Spanish'].map(language=>{
    const rows=skills.filter(item=>item.language===language);
    return `<div class="glass-card skill-card"><p class="eyebrow">${language}</p><h3>Шесть навыков</h3>${rows.map(item=>`<div class="skill-row"><span>${escapeHtml(item.label)}</span><div><i style="width:${item.score}%"></i></div><b>${item.score}%</b></div>`).join('')}</div>`;
  }).join('');
}

async function openLesson(language){
  state.language=language;showView('lesson');
  $$('.mode').forEach(item=>item.classList.toggle('active',item.dataset.lang===language));
  $('#activeAccent').textContent=language==='English'?'American English':'Latin American Spanish';
  try{
    const lesson=await api(`/api/learning/today?language=${language}`);state.currentLesson=lesson;
    $('#activeLanguage').textContent=`${language} • ${lesson.level}`;$('#lessonTitle').textContent=lesson.title;
    $('#lessonObjective').textContent=lesson.objective;$('#lessonMinutes').textContent=`${lesson.minutes} мин`;
    $('#lessonPhrase').textContent=lesson.phrase;$('#writingTask').textContent=lesson.writing_task;
    $('#lessonSteps').innerHTML=lesson.steps.map((step,index)=>`<div class="lesson-step ${index===0?'active':''}"><b>${index+1}</b><span>${escapeHtml(step)}</span></div>`).join('');
    $('#tutorInput').value=`Проведи урок «${lesson.title}». Цель: ${lesson.objective}.`;
    setMascotMood($('#lessonMascot'),'idle');
    const status=$('#mascotStatus');if(status)status.textContent=`Готова к уроку «${lesson.title}».`;
  }catch(error){$('#lessonTitle').textContent=error.message}
}
$$('.language-card').forEach(button=>button.onclick=()=>openLesson(button.dataset.language));
$$('.mode').forEach(button=>button.onclick=()=>openLesson(button.dataset.lang));

$('#tutorForm').addEventListener('submit',async event=>{
  event.preventDefault();const input=$('#tutorInput'),text=input.value.trim();if(!text)return;
  $('#chatMessages').insertAdjacentHTML('beforeend',`<div class="message user"><p>${escapeHtml(text)}</p></div>`);input.value='';
  setMascotMood($('#lessonMascot'),'talk');
  const status=$('#mascotStatus');if(status)status.textContent='Сверяюсь с Obsidian и вашими ошибками…';
  const row=document.createElement('div');row.className='message-row';
  row.innerHTML=`${mascotHTML('talk','sm')}<div class="message tutor">Линни сверяется с маршрутом…</div>`;
  $('#chatMessages').append(row);
  const wait=row.querySelector('.message');
  try{
    const data=await api('/api/tutor/respond',{method:'POST',json:{language:state.language,level:state.currentLesson?.level||'A0',message:text}});
    wait.innerHTML=`<b>Линни</b><p>${escapeHtml(data.answer)}</p><p><strong>Практика:</strong> ${escapeHtml(data.exercise)}</p><small>${data.mode==='demo'?'Демо-режим':'OpenAI + RAG'} • не более 2 замечаний</small>`;
    setMascotMood(row.querySelector('.mascot'),'happy');setMascotMood($('#lessonMascot'),'happy');
    if(status)status.textContent='Урок готов. Повторите фразу вслух.';
    $('#sourceList').innerHTML=data.sources.length?data.sources.map(source=>`<p>▤ ${escapeHtml(source.title)}<br><small>${escapeHtml(source.path)}</small></p>`).join(''):'Материал не найден — ответ ограничен.';
  }catch(error){wait.textContent=error.message;setMascotMood($('#lessonMascot'),'idle')}
  $('#chatMessages').scrollTop=$('#chatMessages').scrollHeight;
});

$('#completeLesson').onclick=async()=>{
  if(!state.currentLesson)return;
  try{
    const data=await api('/api/learning/complete',{method:'POST',json:{lesson_id:state.currentLesson.id,language:state.language,minutes:state.currentLesson.minutes,practiced_skills:['speaking','listening','reading','writing','vocabulary','pronunciation']}});
    $('#completeResult').textContent=data.already_completed?'Этот урок уже учтён.':'Урок завершён: +20 XP. Следующий маршрут открыт.';
    $$('.lesson-step').forEach(item=>item.classList.add('done'));loadDashboard();
  }catch(error){$('#completeResult').textContent=error.message}
};

$('#reflectionForm').addEventListener('submit',async event=>{
  event.preventDefault();if(!state.currentLesson)return;
  try{
    await api('/api/reflections',{method:'POST',json:{language:state.language,lesson_id:state.currentLesson.id,confidence:Number($('#confidence').value),learned:$('#learned').value,difficult:$('#difficult').value}});
    $('#reflectionResult').textContent='Рефлексия сохранена. Она поможет настроить повторение.';event.target.reset();
  }catch(error){$('#reflectionResult').textContent=error.message}
});

async function loadReviews(){
  try{
    const rows=await api('/api/reviews');
    $('#reviewList').innerHTML=rows.length?rows.map(item=>`<div class="review-item"><span class="review-lang">${item.language==='English'?'EN':'ES'}</span><div><b>${escapeHtml(item.example)}</b><p>${item.due?'Пора повторить':'Запланировано на '+new Date(item.next_review_at).toLocaleDateString('ru-RU')}</p></div></div>`).join(''):'<div class="empty-state"><b>Очередь пока пуста</b><p>Ошибки после второй попытки автоматически появятся здесь.</p></div>';
  }catch(error){$('#reviewList').textContent=error.message}
}

async function loadIntegrations(){try{const data=await api('/api/integrations');$('#openaiState').textContent=data.openai==='configured'?'Подключено':'Демо';$('#youtubeState').textContent=data.youtube==='configured'?'API подключён':'Ручной поиск'}catch{}}
$('#reindex').onclick=async()=>{try{const data=await api('/api/admin/rag/reindex',{method:'POST'});$('#reindexResult').textContent=`Готово: проиндексировано документов — ${data.documents}.`}catch(error){$('#reindexResult').textContent=error.message}};

async function loadVideos(){try{const list=await api('/api/videos?language=English');if(list[0])$('#videoLink').href=list[0].url}catch{}}
$('#switchPhrase').onclick=async()=>{state.language=state.language==='English'?'Spanish':'English';$('#practicePhrase').textContent=state.language==='English'?'I think three times.':'Una casa bonita.';const list=await api('/api/videos?language='+state.language);if(list[0])$('#videoLink').href=list[0].url};

let recorder,chunks=[];
$('#recordBtn').onclick=async()=>{try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});recorder=new MediaRecorder(stream);chunks=[];recorder.ondataavailable=event=>chunks.push(event.data);recorder.onstop=()=>{state.blob=new Blob(chunks,{type:'audio/webm'});$('#playback').src=URL.createObjectURL(state.blob);$('#playback').classList.remove('hidden');$('#saveVoice').classList.remove('hidden');stream.getTracks().forEach(track=>track.stop())};  recorder.start();setMascotMood($('#phonoMascot'),'listen');$('#micPulse').classList.add('live');$('#recordStatus').textContent='Линни слушает. Повторите фразу.';$('#recordBtn').disabled=true;$('#stopBtn').disabled=false}catch{$('#recordStatus').textContent='Разрешите доступ к микрофону в браузере.'}};
$('#stopBtn').onclick=()=>{if(recorder?.state==='recording')recorder.stop();setMascotMood($('#phonoMascot'),'happy');$('#micPulse').classList.remove('live');$('#recordStatus').textContent='Запись готова. Прослушайте и сохраните.';$('#recordBtn').disabled=false;$('#stopBtn').disabled=true};
$('#saveVoice').onclick=async()=>{if(!state.blob)return;const form=new FormData();form.append('audio',state.blob,'practice.webm');try{await api('/api/voice?language='+state.language,{method:'POST',body:form});$('#recordStatus').textContent='Линни сохранила запись в кабинете.';setMascotMood($('#phonoMascot'),'idle');$('#saveVoice').classList.add('hidden');loadDashboard()}catch(error){$('#recordStatus').textContent=error.message}};

hydrateMascots();
if(state.token)showApp();else showLogin();
