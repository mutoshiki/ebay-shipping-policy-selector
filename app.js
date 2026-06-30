(() => {
  'use strict';
  const DB = window.FILM_DB;
  if (!DB) throw new Error('Database could not be loaded.');

  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => [...root.querySelectorAll(s)];
  const fmtNum = (v, d=0) => new Intl.NumberFormat('ja-JP',{maximumFractionDigits:d}).format(v);
  const fmtG = v => `${fmtNum(v,1)}g`;
  const fmtUsd = v => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2}).format(v);
  const fmtYen = v => `約${new Intl.NumberFormat('ja-JP',{style:'currency',currency:'JPY',maximumFractionDigits:0}).format(v)}`;
  const normalize = value => String(value ?? '').normalize('NFKC').toLowerCase().replace(/µ/g,'mju').replace(/[^a-z0-9ぁ-んァ-ヶ一-龠]+/g,'');
  const escapeHtml = v => String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const debounce = (fn,wait=120) => {let t;return (...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),wait)}};
  const byId = new Map(DB.items.map(item => [item.id,item]));
  const genreMap = new Map(DB.genres.map(g => [g.genre,g]));
  let selectedItem = null;
  let localSelectedItem = null;
  let dbPage = 1;
  let dbMode = 'cards';
  const pageSize = 30;
  const extras = [
    {id:'strap',label:'ストラップ',g:70},{id:'case',label:'ケース',g:180},{id:'film',label:'フィルム1本',g:30},
    {id:'battery',label:'電池',g:45},{id:'caps',label:'前後キャップ',g:30},{id:'hood',label:'レンズフード',g:45},
    {id:'box',label:'元箱',g:120},{id:'manual',label:'説明書',g:80}
  ];
  const activeExtras = new Set();
  let localMeasurements = loadLocal();
  let toastTimer;
  const memoryStorage = new Map();
  function storageGet(key){ try { return window.localStorage.getItem(key); } catch { return memoryStorage.get(key) ?? null; } }
  function storageSet(key,value){ try { window.localStorage.setItem(key,value); } catch { memoryStorage.set(key,String(value)); } }

  function loadLocal(){
    try { const value=JSON.parse(storageGet('filmCameraMeasurements')||'[]'); return Array.isArray(value)?value:[]; }
    catch { return []; }
  }
  function saveLocal(){storageSet('filmCameraMeasurements',JSON.stringify(localMeasurements));}
  function localFor(item){
    if(!item) return null;
    return localMeasurements.find(x => x.itemId===item.id) || localMeasurements.find(x => normalize(x.name)===normalize(item.name));
  }
  function showToast(message){
    const el=$('#toast'); clearTimeout(toastTimer); el.textContent=message;el.hidden=false;
    toastTimer=setTimeout(()=>el.hidden=true,1900);
  }
  function typeLabel(kind){return kind==='camera'?'カメラ':kind==='lens'?'レンズ':'アクセサリー';}
  function dataLabel(item){
    const local=localFor(item); if(local && Number(local.bareWeight)>0) return {text:'端末の実測',cls:'local'};
    return item.dataType==='reference'?{text:`${item.confidence||'B'} 参考重量`,cls:'reference'}:{text:'D ジャンル推定',cls:'estimate'};
  }
  function effectiveWeight(item){
    const local=localFor(item);
    if(local && Number(local.bareWeight)>0) return {value:Number(local.bareWeight),min:Number(local.bareWeight),max:Number(local.bareWeight),type:'local'};
    if(item.weightG!=null) return {value:Number(item.weightG),min:Number(item.weightG),max:Number(item.weightG),type:'reference'};
    return {value:Number(item.weightMaxG),min:Number(item.weightMinG),max:Number(item.weightMaxG),type:'estimate'};
  }
  function itemWeightText(item){
    const w=effectiveWeight(item);
    return w.type==='estimate'?`${fmtG(w.min)}〜${fmtG(w.max)}`:fmtG(w.value);
  }
  function scoreItem(item, query){
    const q=normalize(query); if(!q) return 0;
    const name=normalize(item.name), brand=normalize(item.brand), all=normalize(item.searchText);
    if(name===q) return 1000;
    if(brand+name===q) return 950;
    if(name.startsWith(q)) return 800-Math.min(name.length-q.length,100);
    if(all.startsWith(q)) return 700;
    if(name.includes(q)) return 620-Math.min(name.indexOf(q),100);
    if(all.includes(q)) return 500-Math.min(all.indexOf(q),100);
    const tokens=String(query).normalize('NFKC').toLowerCase().split(/\s+/).map(normalize).filter(Boolean);
    const hits=tokens.filter(t=>all.includes(t)).length;
    if(tokens.length>1 && hits<tokens.length) return -1;
    return hits ? 220+hits*55 : -1;
  }
  function searchItems(query, limit=12, filters={}){
    const q=String(query||'').trim();
    let rows=DB.items;
    if(filters.kind) rows=rows.filter(x=>x.kind===filters.kind);
    if(filters.brand) rows=rows.filter(x=>x.brand===filters.brand);
    if(filters.genre) rows=rows.filter(x=>x.genre===filters.genre);
    if(filters.mount) rows=rows.filter(x=>(x.mount||'')===filters.mount);
    if(filters.quality){
      if(filters.quality==='local') rows=rows.filter(x=>localFor(x));
      else rows=rows.filter(x=>x.dataType===filters.quality);
    }
    if(!q) return rows.slice(0,limit).map(item=>({item,score:0}));
    return rows.map(item=>({item,score:scoreItem(item,q)})).filter(x=>x.score>=0).sort((a,b)=>b.score-a.score || a.item.name.localeCompare(b.item.name)).slice(0,limit);
  }

  function setView(view){
    $$('.nav-button').forEach(b=>b.classList.toggle('is-active',b.dataset.view===view));
    $$('[data-view-panel]').forEach(panel=>{const active=panel.dataset.viewPanel===view;panel.hidden=!active;panel.classList.toggle('is-active',active)});
    history.replaceState(null,'',`#${view}`);
    if(view==='database') renderDatabase();
    if(view==='genres') renderGenres();
    if(view==='data') renderLocalData();
    window.scrollTo({top:0,behavior:'smooth'});
  }
  $$('.nav-button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));

  function initTheme(){
    const saved=storageGet('filmCameraTheme');
    if(saved) document.documentElement.dataset.theme=saved;
    else if(matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.dataset.theme='dark';
    $('#themeToggle').addEventListener('click',()=>{
      const next=document.documentElement.dataset.theme==='dark'?'light':'dark';
      document.documentElement.dataset.theme=next;storageSet('filmCameraTheme',next);
    });
  }

  function renderSuggestions(container, query, onSelect, limit=9){
    const results=searchItems(query,limit);
    if(!query.trim() || !results.length){container.hidden=true;container.innerHTML='';return;}
    container.innerHTML=results.map(({item},i)=>{
      const badge=dataLabel(item);
      return `<button type="button" class="suggestion" role="option" data-item-id="${escapeHtml(item.id)}" aria-selected="${i===0}"><span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.brand)} · ${escapeHtml(item.genreJa)}</small></span><span class="suggestion-weight">${escapeHtml(itemWeightText(item))}<small>${escapeHtml(badge.text)}</small></span></button>`;
    }).join('');
    container.hidden=false;
    $$('.suggestion',container).forEach(b=>b.addEventListener('click',()=>{onSelect(byId.get(b.dataset.itemId));container.hidden=true;}));
  }

  function selectItem(item){
    selectedItem=item; $('#productSearch').value=item.name;
    const badge=dataLabel(item),w=effectiveWeight(item),local=localFor(item);
    $('#selectedItemCard').classList.remove('empty-state-small');
    $('#selectedItemCard').innerHTML=`<div class="selected-title"><div><span class="item-brand">${escapeHtml(item.brand)}</span><h3>${escapeHtml(item.name)}</h3></div><button type="button" id="clearSelected">選択解除</button></div><div class="selected-meta"><span class="tag">${escapeHtml(typeLabel(item.kind))}</span><span class="tag">${escapeHtml(item.genreJa)}</span>${item.format?`<span class="tag">${escapeHtml(item.format)}</span>`:''}${item.mount?`<span class="tag">${escapeHtml(item.mount)}</span>`:''}<span class="quality-badge ${badge.cls}">${escapeHtml(badge.text)}</span></div><div class="selected-weight"><div><span>${w.type==='estimate'?'推定重量範囲':'本体・商品重量'}</span><strong>${escapeHtml(itemWeightText(item))}</strong></div><div><span>重量条件</span><strong>${escapeHtml(local?.note || item.weightCondition || '—')}</strong></div></div>`;
    $('#clearSelected').addEventListener('click',clearSelectedItem);
    $('#baseWeight').value=Math.round(w.value);
    $('#packingWeight').value=item.packingMaxG;
    $('#packingHelp').textContent=`${fmtG(item.packingMinG)}〜${fmtG(item.packingMaxG)}が目安。安全側の上限を入力済み`;
    $('#baseWeightHelp').textContent=w.type==='estimate'?`同ジャンルの${fmtG(w.min)}〜${fmtG(w.max)}から安全側を採用`:(w.type==='local'?'保存済みの実測値を使用':'公開仕様の代表値。実物との差に注意');
    updateCalculatedWeight();
  }
  function clearSelectedItem(){
    selectedItem=null;$('#productSearch').value='';$('#baseWeight').value='';
    $('#selectedItemCard').className='selected-item empty-state-small';$('#selectedItemCard').textContent='商品を選ぶと、重量と梱包目安を表示します。';updateCalculatedWeight();
  }

  function renderExtraPresets(){
    $('#extraPresets').innerHTML=extras.map(e=>`<button class="extra-chip" type="button" data-extra="${e.id}">${e.label}<small>+${e.g}g</small></button>`).join('');
    $$('.extra-chip').forEach(b=>b.addEventListener('click',()=>{const id=b.dataset.extra;activeExtras.has(id)?activeExtras.delete(id):activeExtras.add(id);b.classList.toggle('is-active',activeExtras.has(id));updateCalculatedWeight()}));
    $('#clearExtras').addEventListener('click',()=>{activeExtras.clear();$$('.extra-chip').forEach(x=>x.classList.remove('is-active'));$('#customExtra').value=0;updateCalculatedWeight()});
  }
  function extraWeight(){return [...activeExtras].reduce((sum,id)=>sum+(extras.find(e=>e.id===id)?.g||0),0)+(Number($('#customExtra').value)||0);}
  function currentWeight(){
    const mode=$('input[name="weightMode"]:checked').value;
    if(mode==='measured') return Number($('#measuredWeight').value)||0;
    return (Number($('#baseWeight').value)||0)+(Number($('#packingWeight').value)||0)+extraWeight();
  }
  function updateCalculatedWeight(){
    const value=currentWeight(),mode=$('input[name="weightMode"]:checked').value;
    $('#calculatedWeight').textContent=value>0?fmtG(value):'—';
    if(mode==='measured') $('#weightSummaryNote').textContent=value>0?'梱包後の実測値をそのまま使用':'梱包後重量を入力してください';
    else if(value>0) $('#weightSummaryNote').textContent=`商品 ${fmtG(Number($('#baseWeight').value)||0)} ＋ 梱包・付属品 ${fmtG(value-(Number($('#baseWeight').value)||0))}`;
    else $('#weightSummaryNote').textContent='商品を選択するか重量を入力してください';
  }
  $$('input[name="weightMode"]').forEach(r=>r.addEventListener('change',()=>{
    const measured=r.value==='measured'&&r.checked;$('#estimateControls').hidden=measured;$('#measuredControls').hidden=!measured;updateCalculatedWeight();
  }));
  ['baseWeight','packingWeight','customExtra','measuredWeight'].forEach(id=>$('#'+id).addEventListener('input',updateCalculatedWeight));

  function choosePolicy(weight,price){
    const tier=DB.policies.tiers.find(t=>weight<=t.maxWeight);
    const priceTier=DB.policies.priceTiers.find(t=>price<=t.maxPrice);
    if(!tier||!priceTier) return {tier,priceTier,manual:true};
    return {tier,priceTier,manual:false,name:`CAM${tier.code}${priceTier.code}`};
  }
  function judge(event){
    event.preventDefault();
    const price=Number($('#priceUsd').value),weight=currentWeight(),rate=Number($('#exchangeRate').value)||156;
    $('#priceError').textContent=price>0?'':'0より大きい商品価格を入力してください。';
    if(!(price>0)){ $('#priceUsd').focus(); return; }
    if(!(weight>0)){ showToast('判定に使う重量を入力してください'); return; }
    storageSet('filmCameraExchangeRate',String(rate));
    const result=choosePolicy(weight,price),product=selectedItem?.name || $('#productSearch').value.trim() || '商品名未入力';
    $('#resultEmpty').hidden=true;$('#resultContent').hidden=false;
    $('#resultProduct').textContent=product;$('#resultWeight').textContent=fmtG(weight);$('#resultPrice').textContent=`${fmtUsd(price)}（${fmtYen(price*rate)}）`;
    $('#rateCaption').textContent=`1 USD = ${fmtNum(rate,2)}円`;
    $('#resultWarning').hidden=true;$('#resultManual').hidden=true;
    if(result.manual){
      $('#resultStatus').textContent='個別確認';$('#resultStatus').className='status manual';
      $('#policyName').textContent='既存ポリシー対象外';$('#resultWeightTier').textContent=weight>2000?'2000g超':'—';$('#resultPriceTier').textContent=price>250?'250USD超':'—';
      $('#shippingCards').innerHTML='';
      const reasons=[];if(weight>2000)reasons.push('重量が2000gを超えています');if(price>250)reasons.push('商品価格が250USDを超えています');
      $('#resultManual').textContent=`${reasons.join('。')}。実送料、補償、署名、EU向けDDP費用を個別に確認してください。`;$('#resultManual').hidden=false;
    }else{
      $('#resultStatus').textContent='判定完了';$('#resultStatus').className='status ready';$('#policyName').textContent=result.name;
      $('#resultWeightTier').textContent=result.tier.label;$('#resultPriceTier').textContent=result.priceTier.label;
      const us=result.priceTier.code==='100USD'?result.tier.usLow:result.tier.usHigh;
      const cards=[['米国',us,'US向け送料一覧',true],['EU27',result.tier.eu,'EU対応送料一覧',false],['その他の対応国',result.tier.intl,'英国・スイスなど',false],['国際基準送料',result.tier.fallback,'送料一覧外の地域',false]];
      $('#shippingCards').innerHTML=cards.map(([label,usd,note,primary])=>`<div class="shipping-card ${primary?'primary':''}"><span>${label}</span><strong>${fmtUsd(usd)}</strong><small>${fmtYen(usd*rate)} · ${note}</small></div>`).join('');
      const warnings=[];
      const remain=result.tier.maxWeight-weight;if(remain>=0&&remain<=20){const next=DB.policies.tiers[DB.policies.tiers.indexOf(result.tier)+1];if(next)warnings.push(`上限まで残り${fmtG(remain)}です。計量誤差がある場合は${next.code}区分が安全です。`)}
      const weightMode=$('input[name="weightMode"]:checked').value;
      if(weightMode!=='measured') warnings.push('推定重量による仮判定です。出品・発送前に梱包後重量を実測してください。');
      if(weightMode!=='measured' && selectedItem?.dataType==='genre-estimate'&&!localFor(selectedItem)) {
        warnings.push('この商品の個別重量は未収録のため、同ジャンルの上限寄りで計算しています。');
        const low=Number(selectedItem.weightMinG||0)+Number(selectedItem.packingMinG||0)+extraWeight();
        const high=Number(selectedItem.weightMaxG||0)+Number(selectedItem.packingMaxG||0)+extraWeight();
        const lowTier=DB.policies.tiers.find(t=>low<=t.maxWeight), highTier=DB.policies.tiers.find(t=>high<=t.maxWeight);
        if(lowTier && highTier && lowTier.code!==highTier.code) warnings.push(`推定範囲では${lowTier.code}〜${highTier.code}にまたがるため、現在は安全側の${highTier.code}で判定しています。`);
      }
      if(warnings.length){$('#resultWarning').textContent=warnings.join(' ');$('#resultWarning').hidden=false;}
    }
    requestAnimationFrame(()=>{if(innerWidth<1000)$('#resultPanel').scrollIntoView({behavior:'smooth',block:'start'})});
  }

  function renderDatasetSummary(){
    const m=DB.meta;$('#datasetSummary').innerHTML=[['収録商品',`${fmtNum(m.recordCount)}件`],['参考重量あり',`${fmtNum(m.referenceCount)}件`],['カメラ・レンズ',`${fmtNum(m.cameraCount+m.lensCount)}件`],['ジャンル',`${fmtNum(m.genreCount)}分類`]].map(([l,v])=>`<div class="summary-stat"><strong>${v}</strong><span>${l}</span></div>`).join('');
    $('#footerMeta').textContent=`データベース ${fmtNum(m.recordCount)}件（参考重量 ${fmtNum(m.referenceCount)}件／ジャンル推定 ${fmtNum(m.recordCount-m.referenceCount)}件）`;
  }

  function populateFilters(){
    const brands=[...new Set(DB.items.map(x=>x.brand))].sort((a,b)=>a.localeCompare(b));
    $('#brandFilter').insertAdjacentHTML('beforeend',brands.map(x=>`<option>${escapeHtml(x)}</option>`).join(''));
    const mounts=[...new Set(DB.items.map(x=>x.mount).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
    $('#mountFilter').insertAdjacentHTML('beforeend',mounts.map(x=>`<option>${escapeHtml(x)}</option>`).join(''));
    const genres=[...DB.genres].sort((a,b)=>a.genreJa.localeCompare(b.genreJa));
    const options=genres.map(x=>`<option value="${escapeHtml(x.genre)}">${escapeHtml(x.genreJa)}（${x.count}）</option>`).join('');
    $('#genreFilter').insertAdjacentHTML('beforeend',options);$('#genreEstimateSelect').innerHTML=options;$('#localGenre').innerHTML=options;
  }
  function databaseRows(){
    const filters={kind:$('#kindFilter').value,brand:$('#brandFilter').value,genre:$('#genreFilter').value,mount:$('#mountFilter').value,quality:$('#qualityFilter').value};
    const query=$('#dbSearch').value.trim();
    let rows=searchItems(query,DB.items.length,filters);
    const sort=$('#sortFilter').value;
    if(sort==='name')rows.sort((a,b)=>a.item.name.localeCompare(b.item.name));
    if(sort==='weightAsc')rows.sort((a,b)=>effectiveWeight(a.item).value-effectiveWeight(b.item).value);
    if(sort==='weightDesc')rows.sort((a,b)=>effectiveWeight(b.item).value-effectiveWeight(a.item).value);
    if(sort==='yearDesc')rows.sort((a,b)=>(b.item.year||0)-(a.item.year||0));
    return rows.map(x=>x.item);
  }
  function itemCard(item){const q=dataLabel(item);return `<article class="item-card" data-open-item="${escapeHtml(item.id)}" tabindex="0"><div class="item-card-header"><div><span class="item-brand">${escapeHtml(item.brand)}</span><h3>${escapeHtml(item.name)}</h3></div><span class="quality-badge ${q.cls}">${escapeHtml(q.text)}</span></div><div class="selected-meta"><span class="tag">${escapeHtml(typeLabel(item.kind))}</span><span class="tag">${escapeHtml(item.genreJa)}</span></div><div class="item-weight"><strong>${escapeHtml(itemWeightText(item))}</strong><small>${escapeHtml(item.weightCondition)}</small></div><div class="item-card-footer"><span>${escapeHtml(item.mount||item.format||'形式不明')}</span><span>${item.year||'発売年不明'}</span></div></article>`}
  function bindOpenItems(root=document){
    $$('[data-open-item]',root).forEach(el=>{const open=()=>openItemDialog(byId.get(el.dataset.openItem));el.addEventListener('click',open);el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}})});
  }
  function renderCoverage(){
    const brands=[...new Set(DB.items.map(x=>x.brand))].map(brand=>{
      const rows=DB.items.filter(x=>x.brand===brand), refs=rows.filter(x=>x.dataType==='reference').length;
      return {brand,total:rows.length,refs,ratio:rows.length?refs/rows.length:0};
    }).sort((a,b)=>b.total-a.total).slice(0,12);
    const exactB=DB.items.filter(x=>x.dataType==='reference'&&x.confidence==='B').length;
    const exactC=DB.items.filter(x=>x.dataType==='reference'&&x.confidence==='C').length;
    $('#coveragePanel').innerHTML=`<div class="coverage-head"><div><p class="eyebrow">COVERAGE</p><h2>データ収録状況</h2></div><p>参考重量 ${fmtNum(DB.meta.referenceCount)}件（B ${fmtNum(exactB)}件／C ${fmtNum(exactC)}件）、未確認機種はジャンル分布で推定</p></div><div class="coverage-bars">${brands.map(b=>`<div class="coverage-row"><span>${escapeHtml(b.brand)}</span><div><i style="width:${Math.max(2,b.ratio*100)}%"></i></div><small>${b.refs}/${b.total}</small></div>`).join('')}</div>`;
  }

  function renderDatabase(){
    const rows=databaseRows(),pages=Math.max(1,Math.ceil(rows.length/pageSize));dbPage=Math.min(dbPage,pages);const start=(dbPage-1)*pageSize,current=rows.slice(start,start+pageSize);
    $('#dbCount').textContent=`${fmtNum(rows.length)}件を表示（全${fmtNum(DB.meta.recordCount)}件）`;
    $('#pageInfo').textContent=`${dbPage} / ${pages}`;$('#prevPage').disabled=dbPage<=1;$('#nextPage').disabled=dbPage>=pages;
    if(dbMode==='cards'){$('#dbCards').hidden=false;$('#dbTableWrap').hidden=true;$('#dbCards').innerHTML=current.map(itemCard).join('');bindOpenItems($('#dbCards'));}
    else{$('#dbCards').hidden=true;$('#dbTableWrap').hidden=false;$('#dbTableBody').innerHTML=current.map(item=>{const q=dataLabel(item);return `<tr data-open-item="${escapeHtml(item.id)}"><td><strong>${escapeHtml(item.name)}</strong><br><small>${escapeHtml(item.brand)}</small></td><td>${escapeHtml(item.genreJa)}</td><td>${escapeHtml(item.format||'—')}</td><td>${escapeHtml(item.mount||'—')}</td><td>${escapeHtml(itemWeightText(item))}</td><td><span class="quality-badge ${q.cls}">${escapeHtml(q.text)}</span></td><td>${item.year||'—'}</td></tr>`}).join('');bindOpenItems($('#dbTableBody'));}
  }
  const resetDb=()=>{dbPage=1;renderDatabase()};
  $('#dbSearch').addEventListener('input',debounce(resetDb));['kindFilter','brandFilter','genreFilter','mountFilter','qualityFilter','sortFilter'].forEach(id=>$('#'+id).addEventListener('change',resetDb));
  $('#prevPage').addEventListener('click',()=>{dbPage--;renderDatabase();scrollTo({top:0,behavior:'smooth'})});$('#nextPage').addEventListener('click',()=>{dbPage++;renderDatabase();scrollTo({top:0,behavior:'smooth'})});
  $$('[data-db-view]').forEach(b=>b.addEventListener('click',()=>{dbMode=b.dataset.dbView;$$('[data-db-view]').forEach(x=>x.classList.toggle('is-active',x===b));renderDatabase()}));

  function openItemDialog(item){
    const q=dataLabel(item),w=effectiveWeight(item),g=genreMap.get(item.genre),local=localFor(item);
    const target=(w.min+w.max)/2;
    const similar=DB.items.filter(x=>x.id!==item.id&&x.genre===item.genre&&x.dataType==='reference').sort((a,b)=>Math.abs(Number(a.weightG)-target)-Math.abs(Number(b.weightG)-target)).slice(0,6);
    const similarHtml=similar.length?`<section class="similar-section"><h3>近いジャンルの参考機種</h3><div class="similar-list">${similar.map(x=>`<button type="button" data-similar-id="${escapeHtml(x.id)}"><span>${escapeHtml(x.name)}</span><strong>${fmtG(x.weightG)}</strong></button>`).join('')}</div></section>`:'';
    $('#dialogContent').innerHTML=`<div class="dialog-body"><span class="item-brand">${escapeHtml(item.brand)} · ${escapeHtml(typeLabel(item.kind))}</span><h2>${escapeHtml(item.name)}</h2><div class="selected-meta"><span class="tag">${escapeHtml(item.genreJa)}</span>${item.format?`<span class="tag">${escapeHtml(item.format)}</span>`:''}${item.mount?`<span class="tag">${escapeHtml(item.mount)}</span>`:''}<span class="quality-badge ${q.cls}">${escapeHtml(q.text)}</span></div><div class="dialog-weight"><div><span>${w.type==='estimate'?'推定重量範囲':'本体・商品重量'}</span><strong>${escapeHtml(itemWeightText(item))}</strong></div><div><span>安全側の推定梱包後重量</span><strong>${fmtG(w.value+item.packingMaxG)}</strong></div></div><dl class="detail-list"><div><dt>重量条件</dt><dd>${escapeHtml(local?.note||item.weightCondition||'—')}</dd></div><div><dt>梱包材の目安</dt><dd>+${fmtG(item.packingMinG)}〜${fmtG(item.packingMaxG)}</dd></div><div><dt>マウント</dt><dd>${escapeHtml(item.mount||'—')}</dd></div><div><dt>フォーカス</dt><dd>${escapeHtml(item.focus||'—')}</dd></div><div><dt>レンズ方式</dt><dd>${escapeHtml(item.lensType||'—')}</dd></div><div><dt>発売年</dt><dd>${item.year||'—'}</dd></div><div><dt>同ジャンル登録数</dt><dd>${g?.count||0}件（参考重量 ${g?.referenceCount||0}件）</dd></div><div><dt>データ品質</dt><dd>${escapeHtml(q.text)}</dd></div></dl>${item.dataType==='genre-estimate'?`<div class="warning-box">この機種の個別重量は未確認です。${escapeHtml(item.genreJa)}の既知データから${fmtG(item.weightMinG)}〜${fmtG(item.weightMaxG)}と推定しています。</div>`:''}${similarHtml}<div class="dialog-actions"><button type="button" class="use-item">配送判定に使う</button><button type="button" class="browse-genre">同ジャンルを見る</button></div></div>`;
    $('.use-item',$('#dialogContent')).addEventListener('click',()=>{$('#itemDialog').close();selectItem(item);setView('judge')});
    $('.browse-genre',$('#dialogContent')).addEventListener('click',()=>{$('#itemDialog').close();$('#genreEstimateSelect').value=item.genre;renderGenreEstimate();setView('genres')});
    $$('[data-similar-id]',$('#dialogContent')).forEach(b=>b.addEventListener('click',()=>openItemDialog(byId.get(b.dataset.similarId))));
    if($('#itemDialog').open) return;
    $('#itemDialog').showModal();
  }
  $('#closeDialog').addEventListener('click',()=>$('#itemDialog').close());$('#itemDialog').addEventListener('click',e=>{if(e.target===$('#itemDialog'))$('#itemDialog').close()});

  function renderGenreEstimate(){
    const g=genreMap.get($('#genreEstimateSelect').value);if(!g)return;
    $('#genreEstimateResult').innerHTML=[['登録数',`${g.count}件`],['参考重量',`${g.referenceCount}件`],['よくある本体重量',`${fmtG(g.typicalLowG)}〜${fmtG(g.typicalHighG)}`],['安全側の梱包加算',`+${fmtG(g.packingMaxG)}`]].map(([l,v])=>`<div class="estimate-stat"><span>${l}</span><strong>${v}</strong></div>`).join('');
    const refs=DB.items.filter(x=>x.genre===g.genre&&x.dataType==='reference').sort((a,b)=>a.weightG-b.weightG).slice(0,12);
    $('#genreReferenceExamples').innerHTML=refs.length?`<h3>このジャンルの参考機種</h3><div>${refs.map(x=>`<button type="button" data-genre-ref="${escapeHtml(x.id)}"><span>${escapeHtml(x.name)}</span><strong>${fmtG(x.weightG)}</strong></button>`).join('')}</div>`:'<p>参考重量を追加中です。</p>';
    $$('[data-genre-ref]',$('#genreReferenceExamples')).forEach(b=>b.addEventListener('click',()=>openItemDialog(byId.get(b.dataset.genreRef))));
  }
  function renderGenres(){
    renderGenreEstimate();const max=Math.max(...DB.genres.map(x=>x.maxG||0));
    $('#genreGrid').innerHTML=[...DB.genres].sort((a,b)=>b.count-a.count).map(g=>{const left=(g.typicalLowG/max)*100,width=Math.max(2,((g.typicalHighG-g.typicalLowG)/max)*100);return `<article class="genre-card" data-genre="${escapeHtml(g.genre)}"><h3>${escapeHtml(g.genreJa)}</h3><p class="genre-count">${g.count}件 · 参考重量 ${g.referenceCount}件</p><div class="range-bar"><span style="left:${left}%;width:${width}%"></span></div><div class="genre-numbers"><span>よくある範囲</span><strong>${fmtG(g.typicalLowG)}〜${fmtG(g.typicalHighG)}</strong></div><p class="genre-examples">例：${escapeHtml((g.examples||[]).slice(0,3).join('、')||'参考重量を追加中')}</p></article>`}).join('');
    $$('.genre-card').forEach(c=>c.addEventListener('click',()=>{$('#genreEstimateSelect').value=c.dataset.genre;renderGenreEstimate();$('#genreEstimateSelect').scrollIntoView({behavior:'smooth',block:'center'})}));
  }
  $('#genreEstimateSelect').addEventListener('change',renderGenreEstimate);
  $('#useGenreEstimate').addEventListener('click',()=>{const g=genreMap.get($('#genreEstimateSelect').value);if(!g)return;const name=$('#unknownProductName').value.trim()||`未登録の${g.genreJa}`;const item={id:`custom-${Date.now()}`,kind:'camera',brand:'未登録',name,aliases:[],genre:g.genre,genreJa:g.genreJa,format:'',focus:'',lensType:'',mount:'',year:null,weightG:null,weightMinG:g.typicalLowG,weightMaxG:g.typicalHighG,weightCondition:'同ジャンルの参考機種から推定',dataType:'genre-estimate',confidence:'D',packingMinG:g.packingMinG,packingMaxG:g.packingMaxG,searchText:name};selectItem(item);setView('judge');showToast('ジャンル推定を判定欄へ反映しました')});

  function selectLocalItem(item){localSelectedItem=item;$('#localProductSearch').value=item.name;$('#localGenre').value=item.genre;const w=effectiveWeight(item);if(w.type!=='estimate')$('#localBareWeight').value=w.value;$('#localSuggestions').hidden=true;}
  function renderLocalData(){
    $('#localCount').textContent=`${localMeasurements.length}件`;
    $('#localList').innerHTML=localMeasurements.length?localMeasurements.map(x=>`<div class="local-entry"><div><h3>${escapeHtml(x.name)}</h3><p>${x.bareWeight?`本体 ${fmtG(x.bareWeight)}`:''}${x.bareWeight&&x.packedWeight?' ／ ':''}${x.packedWeight?`梱包後 ${fmtG(x.packedWeight)}`:''} · ${escapeHtml(genreMap.get(x.genre)?.genreJa||x.genre||'未分類')}</p>${x.note?`<p>${escapeHtml(x.note)}</p>`:''}</div><button type="button" data-delete-local="${escapeHtml(x.id)}">削除</button></div>`).join(''):'<p class="empty-state-small">まだ保存された実測値はありません。</p>';
    $$('[data-delete-local]').forEach(b=>b.addEventListener('click',()=>{localMeasurements=localMeasurements.filter(x=>x.id!==b.dataset.deleteLocal);saveLocal();renderLocalData();renderDatabase();showToast('実測値を削除しました')}));
    $('#sourceList').innerHTML=DB.sources.map(s=>`<div class="source-row"><strong>${s.url?`<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.label)}</a>`:escapeHtml(s.label)}</strong><small>${escapeHtml(s.note)}</small></div>`).join('');
  }
  $('#localForm').addEventListener('submit',e=>{
    e.preventDefault();const name=$('#localProductSearch').value.trim(),bare=Number($('#localBareWeight').value)||null,packed=Number($('#localPackedWeight').value)||null;
    if(!name||(!bare&&!packed)){showToast('商品名と、どちらかの重量を入力してください');return;}
    const entry={id:`local-${Date.now()}`,itemId:localSelectedItem?.id||null,name,brand:localSelectedItem?.brand||'',genre:$('#localGenre').value,bareWeight:bare,packedWeight:packed,note:$('#localNote').value.trim(),updatedAt:new Date().toISOString()};
    localMeasurements=localMeasurements.filter(x=>!(entry.itemId&&x.itemId===entry.itemId)&&normalize(x.name)!==normalize(entry.name));localMeasurements.unshift(entry);saveLocal();
    e.target.reset();localSelectedItem=null;renderLocalData();renderDatabase();showToast('実測値を保存しました');
  });
  $('#exportLocal').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({version:1,measurements:localMeasurements},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='film-camera-measurements.json';a.click();URL.revokeObjectURL(a.href)});
  $('#importLocal').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{const data=JSON.parse(await file.text());const rows=Array.isArray(data)?data:data.measurements;if(!Array.isArray(rows))throw new Error();localMeasurements=rows;saveLocal();renderLocalData();showToast('実測データを読み込みました')}catch{showToast('JSONファイルを読み込めませんでした')}e.target.value=''});

  function initSearches(){
    const product=$('#productSearch'),suggestions=$('#searchSuggestions');product.addEventListener('input',debounce(()=>renderSuggestions(suggestions,product.value,selectItem)));product.addEventListener('focus',()=>renderSuggestions(suggestions,product.value,selectItem));
    const local=$('#localProductSearch'),ls=$('#localSuggestions');local.addEventListener('input',debounce(()=>{localSelectedItem=null;renderSuggestions(ls,local.value,selectLocalItem)}));local.addEventListener('focus',()=>renderSuggestions(ls,local.value,selectLocalItem));
    document.addEventListener('click',e=>{if(!$('#judgeSearchBox').contains(e.target))suggestions.hidden=true;if(!$('#localForm').contains(e.target))ls.hidden=true});
  }

  function init(){
    initTheme();populateFilters();renderExtraPresets();renderDatasetSummary();renderCoverage();initSearches();renderGenres();renderLocalData();
    const savedRate=Number(storageGet('filmCameraExchangeRate'));if(savedRate>0)$('#exchangeRate').value=savedRate;
    $('#judgeForm').addEventListener('submit',judge);$('#copyPolicy').addEventListener('click',async()=>{const t=$('#policyName').textContent;if(!t||t==='既存ポリシー対象外')return;try{await navigator.clipboard.writeText(t)}catch{const ta=document.createElement('textarea');ta.value=t;document.body.append(ta);ta.select();document.execCommand('copy');ta.remove()}showToast('ポリシー名をコピーしました')});
    const initial=(location.hash||'#judge').slice(1);if(['judge','database','genres','data'].includes(initial))setView(initial);
    updateCalculatedWeight();renderDatabase();
  }
  init();
})();
