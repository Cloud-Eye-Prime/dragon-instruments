# Conductor Shell -- reconstruction plan (split UI: chat-left, mixer-artifact-right)

Goal: a sacred-calculator-style split page where the tempo mixer is the ARTIFACT
window (right) and a chat panel runs alongside it on the LEFT, the chat sized +
styled to the S26 webui standard. The mixer's Conductor engine stays the single
source of truth; the left chat is its face (sends intents, mirrors narration).

## The two references (ground truth -- lift from these, do not invent)

STRUCTURE = sacred-calculator/index.html (sunfire-wuji):
  .app{display:flex;flex-direction:column;height:100dvh}
  .main{display:grid;grid-template-columns:minmax(320px,2fr) minmax(360px,3fr)}
  @media(max-width:860px){ .main{grid-template-columns:1fr} + .mtabs tab bar (Chat|Mixer) }
  Left = .chat (log + composer); Right = the artifact panel.

DIMENSIONS/STYLE = hushmaw-hatchery/payloads/webui.py INDEX_HTML (the S26 standard):
  palette: --bg:#0d1117 --panel:#161b22 --ink:#e6edf3 --mut:#8b949e --line:#30363d
           --accent:#39d0c8 --accent2:#7ee787 --you:#1f6feb33 --dragon:#161b22
  #app{display:flex;flex-direction:column;height:100dvh;width:100%;max-width:440px;margin:0 auto}
  #log{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:14px}
  .msg{max-width:90%;padding:11px 14px;border-radius:16px;white-space:pre-wrap}
  .you{align-self:flex-end;background:var(--you);border:1px solid #1f6feb55}
  .dragon{align-self:flex-start;background:var(--dragon);border:1px solid var(--line);
          max-width:95%;font-family:"Noto Serif",Georgia,serif}
  form{display:flex;gap:8px;padding:10px 12px 4px;border-top:1px solid var(--line);align-items:flex-end}
  textarea{flex:1;resize:none;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
  button.send{background:var(--accent);color:#04121a;border:0;border-radius:50%;width:42px;height:42px}
  .tools{display:flex;gap:2px;padding:3px 8px 7px}  (thin icon strip under the input)
  => The LEFT chat column is the 440px phone-width webui column, verbatim palette + metrics.

## Non-negotiable constraints (repo law -- every file obeys)
- ASCII ONLY in source (`--` dashes, straight quotes; CJK/emoji as \u or &#x..; entities).
- The mixer stays ONE self-contained file. The shell is a NEW file. No framework, no npm, no build.
- Backward compat: tempo_mixer.html standalone (no ?embed) must behave EXACTLY as today --
  Console, Conductor, all AI lanes, the /ai relay fallback, everything.
- Validate every edit: node --check the extracted <script>; assert ZERO non-ASCII bytes.

## THE POSTMESSAGE CONTRACT (both sides build to THIS, same-origin)

Parent shell -> iframe mixer  (mixer listens on window 'message'):
  {source:'dragon-shell', type:'hello'}                       -> mixer replies 'ready'
  {source:'dragon-shell', type:'conduct', intent:str, beta:str?} -> mixer: if beta, store it
        (localStorage dragonbridge_beta + #aiBeta); set #cvIntent.value=intent; conductorPlan()
  {source:'dragon-shell', type:'stop'}                        -> conductorStop()
  {source:'dragon-shell', type:'authority', mode:'session'|'breath'|'listener'} -> setAuthority(mode)

iframe mixer -> parent shell  (shell listens on window 'message'):
  {source:'dragon-mixer', type:'ready', ai:bool, beta:bool}   -> on load + on 'hello'
  {source:'dragon-mixer', type:'narrate', line:str, cls:'n'|'warn'|''} -> every cvLog line, mirrored
  {source:'dragon-mixer', type:'status', text:str}            -> every setStatus, mirrored
  {source:'dragon-mixer', type:'authority', mode:str}         -> when authority changes (echo)

Rule: ignore any message whose .source is not the expected peer. postMessage targetOrigin =
location.origin (same-origin). Guard everything with try/catch; a missing peer is silent.

## WORK ITEM A -- mixer bridge (edit public/tempo_mixer.html, ADDITIVE)
Anchors that already exist (edit against these, not memory): cvLog(msg,cls) appends to #cvLog;
conductorPlan(); conductorStop(); setAuthority(m); setConductorMode(on); setStatus(t);
aiBeta() reads localStorage 'dragonbridge_beta'; #aiBeta input; #cvIntent/#cvGo/#cvStop/#cvLog;
#conductorBar; a POST /ai relay + ANTHROPIC key state (window has no direct 'ai' flag -- send
ai:!!aiKey() OR unknown=false; the shell only uses it for a hint).
Changes:
  1. Add a tiny bridge: var EMBED = new URLSearchParams(location.search).has('embed');
     var inFrame = (window.parent && window.parent!==window);
     function toShell(type,extra){ if(!inFrame)return; try{ window.parent.postMessage(
        Object.assign({source:'dragon-mixer',type:type},extra||{}), location.origin);}catch(e){} }
  2. cvLog: after it renders a line, call toShell('narrate',{line:msg,cls:cls||''}).
  3. setStatus: after it sets text, call toShell('status',{text:t}). (Keep it cheap; no loops.)
  4. window 'message' listener: accept only e.data.source==='dragon-shell'; route
     hello->toShell('ready',{ai:!!aiKey(),beta:!!aiBeta()}); conduct-> (store beta if given)
     $('cvIntent').value=intent; conductorPlan(); stop->conductorStop(); authority->setAuthority(mode).
  5. EMBED mode: on load, add body.embed; auto setConductorMode(true); the internal chat widgets
     (#cvIntent,#cvGo,#cvStop,#cvLog) are hidden by CSS `body.embed #cvIntent,...{display:none}`
     -- the shell owns the chat. The time-authority row + mode toggle STAY visible (handy in-frame).
     Post 'ready' once DOM is up.
  6. setAuthority: after switching, toShell('authority',{mode:m}).
Verify: node --check clean; ZERO non-ASCII; standalone (no ?embed) UNCHANGED. Report the exact
message shapes you implemented (must equal the contract).

## WORK ITEM B -- the split shell (NEW file public/conductor.html)
A sacred-calc-structured page, S26-webui-dimensioned chat on the left, mixer iframe on the right.
Layout:
  .app flex column 100dvh; thin header.top ("DRAGON BRIDGE -- Conductor", a link back to ./index.html).
  .main grid: grid-template-columns: minmax(360px,440px) 1fr;  (LEFT = the 440px webui column; RIGHT = artifact)
  LEFT .chat: lift the webui palette + #log/.msg/.you/.dragon/form/textarea/button.send/.tools VERBATIM
       (rename ids to avoid clashes but keep the metrics). Composer = textarea + round 42px send.
       A thin tools strip: a beta-code field (password, stored localStorage dragonbridge_beta and
       sent on conduct), a "stop set" button, and 3 authority chips (Session|Breath|Listener).
       A first .dragon bubble greets: what the Conductor is + "name artists, songs, moods".
  RIGHT .artifact: <iframe id="mix" src="./tempo_mixer.html?embed=1" style="width:100%;height:100%;border:0">
       in a framed panel (border-left:1px solid --line; the mixer is the living artifact).
  @media(max-width:860px): collapse to one panel + a .mtabs bar (Chat | Mixer), sacred-calc pattern;
       textarea font-size:16px to stop iOS zoom.
JS (vanilla, no deps):
  - On submit: append a .you bubble with the intent, clear the textarea, postMessage to the iframe
    {source:'dragon-shell',type:'conduct',intent,beta}. Disable send until the next 'ready'/'status' settles.
  - message listener (source==='dragon-mixer'): 'narrate' -> append/extend a .dragon bubble
    (cls 'warn' -> amber text, 'n' -> accent tint); 'status' -> a subtle status line under the log;
    'ready' -> enable send, note ai/beta availability in the greeting.
  - authority chips -> postMessage {type:'authority',mode}; stop -> {type:'stop'}.
  - iframe onload -> postMessage {source:'dragon-shell',type:'hello'} to fetch 'ready'.
Verify: node --check the shell's <script>; ZERO non-ASCII; loads with no console errors.

## WORK ITEM C -- integration + launcher + deploy (Cloud-Eye, after A+B)
- Reconcile A's implemented shapes against B's expectations (the contract is the referee).
- index.html: add a tile `<a href="./conductor.html">The Conductor -- chat-driven live set</a>` at top.
- Live-verify in the browser preview: shell loads, iframe mounts the mixer, a typed intent posts and
  narration mirrors back into left bubbles, authority chips work, responsive collapse < 860px, no errors.
- Deploy: railway up (heartbeat-pages), probe the live /conductor.
The Dragon proposes the set; the Architect conducts.
