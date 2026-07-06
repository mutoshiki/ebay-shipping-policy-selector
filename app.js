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
  const packingProfiles = new Map((DB.packingProfiles||[]).map(p=>[p.id,p]));
  let currentExtras = [];
  let suppressPackingInput = false;
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
  function localPackingFor(item){
    const local=localFor(item); if(!local) return null;
    const bare=Number(local.bareWeight)||0, packed=Number(local.packedWeight)||0;
    return bare>0&&packed>bare ? packed-bare : null;
  }
  function profileForItem(item){
    return packingProfiles.get(item?.packingProfile) || packingProfiles.get('small-box');
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
    const badge=dataLabel(item),w=effectiveWeight(item),local=localFor(item),profile=profileForItem(item),localPacking=localPackingFor(item);
    $('#selectedItemCard').classList.remove('empty-state-small');
    $('#selectedItemCard').innerHTML=`<div class="selected-title"><div><span class="item-brand">${escapeHtml(item.brand)}</span><h3>${escapeHtml(item.name)}</h3></div><button type="button" id="clearSelected">選択解除</button></div><div class="selected-meta"><span class="tag">${escapeHtml(typeLabel(item.kind))}</span><span class="tag">${escapeHtml(item.genreJa)}</span>${item.format?`<span class="tag">${escapeHtml(item.format)}</span>`:''}${item.mount?`<span class="tag">${escapeHtml(item.mount)}</span>`:''}<span class="quality-badge ${badge.cls}">${escapeHtml(badge.text)}</span></div><div class="selected-weight three"><div><span>${w.type==='estimate'?'推定重量範囲':'本体・商品重量'}</span><strong>${escapeHtml(itemWeightText(item))}</strong></div><div><span>推奨梱包</span><strong>${escapeHtml(profile?.label||'手動')}</strong></div><div><span>梱包加算</span><strong>${fmtG(localPacking ?? item.packingDefaultG ?? profile?.defaultG ?? item.packingMaxG)}</strong></div></div>`;
    $('#clearSelected').addEventListener('click',clearSelectedItem);
    $('#baseWeight').value=Math.round(w.value);
    suppressPackingInput=true;
    if(localPacking!=null){$('#packingProfile').value='custom';$('#packingWeight').value=Math.round(localPacking);$('#packingHelp').textContent=`保存済み実測：梱包後−本体 = ${fmtG(localPacking)}`;}
    else{$('#packingProfile').value=item.packingProfile||profile?.id||'custom';$('#packingWeight').value=Math.round(item.packingDefaultG??profile?.defaultG??item.packingMaxG);$('#packingHelp').textContent=`通常 ${fmtG(item.packingMinG)}〜${fmtG(item.packingMaxG)}。中央の標準値を入力済み`;}
    suppressPackingInput=false;
    $('#baseWeightHelp').textContent=w.type==='estimate'?`同ジャンルの${fmtG(w.min)}〜${fmtG(w.max)}から安全側を採用`:(w.type==='local'?'保存済みの実測値を使用':'公開仕様の代表値。実物との差に注意');
    renderPackingBreakdown();renderExtraPresets(item);updateCalculatedWeight();
  }
  function clearSelectedItem(){
    selectedItem=null;$('#productSearch').value='';$('#baseWeight').value='';$('#packingProfile').value='custom';renderPackingBreakdown();renderExtraPresets(null);
    $('#selectedItemCard').className='selected-item empty-state-small';$('#selectedItemCard').textContent='商品を選ぶと、重量と梱包目安を表示します。';updateCalculatedWeight();
  }

  function accessorySuggestions(item){
    if(!item) return [
      {id:'strap',label:'ストラップ',g:60,note:'一般的な細幅ストラップ'},
      {id:'case',label:'ケース',g:180,note:'サイズにより要修正'},
      {id:'box',label:'元箱',g:140,note:'内装材を含む目安'},
      {id:'manual',label:'説明書',g:45,note:'薄い冊子'}
    ];
    const name=item.name.toLowerCase(), w=effectiveWeight(item).value, out=[];
    const add=(id,label,g,note)=>out.push({id,label,g,note});
    if(/ar-?2|ar-?3/.test(name)){add('release-case','純正小袋・ケース',12,'付属する場合');add('retail-box','元箱',24,'小型紙箱');add('instruction','説明書',7,'折り紙1枚程度');return out;}
    if(/as-1/.test(name)){add('plastic-case','純正ケース',24,'樹脂ケース');add('retail-box','元箱',30,'小型紙箱');add('instruction','説明書',8,'薄紙');return out;}
    if(/focusing screen/.test(name)){add('screen-case','純正スクリーンケース',22,'樹脂ケース');add('outer-box','元箱',18,'小型紙箱');add('insert','ピンセット・台紙',6,'付属する場合');return out;}
    if(/dk-5|eyepiece cap/.test(name)){add('retail-bag','純正袋',3,'小袋');add('multi-pack','追加同一品1個',2,'複数個販売時');return out;}
    if(/dg-2/.test(name)){add('adapter','接眼アダプター',8,'付属する場合');add('plastic-case','純正ケース',38,'樹脂ケース');add('retail-box','元箱',42,'紙箱');return out;}
    if(item.kind==='camera'){
      add('film','35mmフィルム1本',30,'ケース込み');
      if(item.genre.includes('SLR')) add('body-cap','ボディキャップ',12,'ボディ単体出品時'); else add('lens-cap','レンズキャップ',14,'固定レンズ用');
      const batt=item.genre.includes('AF')||item.genre.includes('zoom')?36:12;add('battery','電池1組',batt,'機種により種類が異なるため修正可');
      add('strap','ストラップ',item.genre.includes('Medium')?85:58,'一般的な純正ストラップ');
      add('case','専用ケース',w>700?240:w>400?190:145,'革ケース・ソフトケース');
      add('box','元箱＋内装',w>700?240:w>400?180:130,'箱サイズに応じた標準値');
      add('manual','説明書',w>700?70:48,'冊子');
    }else if(item.kind==='lens'){
      const scale=w>900?1.8:w>450?1.35:1;
      add('front-cap','フロントキャップ',Math.round(14*scale),'口径に合わせて修正可');
      add('rear-cap','リアキャップ',Math.round(18*scale),'マウント別');
      add('filter','保護フィルター',Math.round(22*scale),'口径により変動');
      add('hood','レンズフード',Math.round(42*scale),'金属・大型は重め');
      add('pouch','ソフトケース',Math.round(60*scale),'巾着・ポーチ');
      if(w>650)add('collar','三脚座',w>1200?220:135,'付属する場合');
      add('box','元箱＋内装',Math.round(130*scale),'内装材込み');
      add('manual','説明書',35,'薄い冊子');
    }else{
      if(item.genre==='Flash'){add('battery','電池1組',96,'単3×4本の目安');add('stand','フラッシュスタンド',24,'付属する場合');add('case','専用ケース',80,'ソフトケース');}
      else if(item.genre.includes('finder')||item.genre==='Finder accessory'){add('adapter','接眼アダプター',8,'付属する場合');add('case','純正ケース',55,'樹脂・ソフトケース');}
      else if(item.genre==='Motor drive / winder'){add('battery','電池1組',96,'単3×4本の目安');add('battery-holder','電池ホルダー',35,'付属する場合');}
      else if(item.genre==='Filter / hood'){add('case','フィルターケース',20,'樹脂ケース');}
      else {add('case','純正ケース・袋',28,'付属する場合');}
      add('box','元箱',w>250?95:w>100?55:30,'箱サイズ別の目安');add('manual','説明書',w>250?35:12,'冊子・折り紙');
    }
    return out;
  }
  function renderExtraPresets(item=selectedItem){
    currentExtras=accessorySuggestions(item);
    $('#extraPresets').innerHTML=currentExtras.map(e=>`<label class="accessory-row"><input type="checkbox" data-extra-check="${escapeHtml(e.id)}"><span class="accessory-copy"><strong>${escapeHtml(e.label)}</strong><small>${escapeHtml(e.note||'')}</small></span><span class="accessory-weight"><input type="number" min="0" step="1" value="${e.g}" data-extra-weight="${escapeHtml(e.id)}" aria-label="${escapeHtml(e.label)}の重量"><b>g</b></span></label>`).join('');
    $$('[data-extra-check]').forEach(el=>el.addEventListener('change',updateCalculatedWeight));
    $$('[data-extra-weight]').forEach(el=>el.addEventListener('input',()=>{const cb=$(`[data-extra-check="${CSS.escape(el.dataset.extraWeight)}"]`);if(cb&&!cb.checked)cb.checked=true;updateCalculatedWeight()}));
  }
  function extraWeight(){
    const presets=$$('[data-extra-check]:checked').reduce((sum,cb)=>sum+(Number($(`[data-extra-weight="${CSS.escape(cb.dataset.extraCheck)}"]`)?.value)||0),0);
    return presets+(Number($('#customExtra').value)||0);
  }
  function renderPackingBreakdown(){
    const id=$('#packingProfile').value, p=packingProfiles.get(id), box=$('#packingBreakdown');
    if(!p){box.innerHTML=`<span>梱包内訳</span><p>手動設定 ${fmtG(Number($('#packingWeight').value)||0)}</p>`;return;}
    const total=p.components.reduce((s,x)=>s+Number(x[1]),0), target=Number($('#packingWeight').value)||p.defaultG, ratio=total?target/total:1;
    box.innerHTML=`<span>${escapeHtml(p.method)}・標準 ${fmtG(p.defaultG)}</span><div>${p.components.map(([label,g])=>`<b>${escapeHtml(label)} ${fmtG(Math.round(g*ratio))}</b>`).join('')}</div><p>${escapeHtml(p.note)}</p>`;
  }
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
  ['baseWeight','customExtra','measuredWeight'].forEach(id=>$('#'+id).addEventListener('input',updateCalculatedWeight));
  $('#packingWeight').addEventListener('input',()=>{if(!suppressPackingInput)$('#packingProfile').value='custom';renderPackingBreakdown();updateCalculatedWeight()});
  $('#packingProfile').addEventListener('change',()=>{const p=packingProfiles.get($('#packingProfile').value);if(p){suppressPackingInput=true;$('#packingWeight').value=p.defaultG;suppressPackingInput=false;$('#packingHelp').textContent=`通常 ${fmtG(p.minG)}〜${fmtG(p.maxG)}。標準値を使用`;}renderPackingBreakdown();updateCalculatedWeight()});

  function roundUpX99(value){return Math.round((Math.ceil(value-0.99-1e-9)+0.99)*100)/100;}
  function usOverrideFor(tier,price,rate){
    const m=DB.policies.model;
    const dutyJpy=price*rate*m.dutyRate;
    const totalJpy=tier.transportJpy+m.customsFeeJpy+dutyJpy*(1+m.dutyProcessingRate)+m.packingBufferJpy;
    return roundUpX99(totalJpy/(rate*(1-m.ebayFeeRate)));
  }
  function choosePolicy(weight,price,rate){
    const tier=DB.policies.tiers.find(t=>weight<=t.maxWeight);
    if(!tier) return {tier,manual:true};
    return {tier,manual:false,name:tier.policyName,usOverride:usOverrideFor(tier,price,rate)};
  }
  function judge(event){
    event.preventDefault();
    const price=Number($('#priceUsd').value),weight=currentWeight(),rate=Number($('#exchangeRate').value)||150;
    $('#priceError').textContent=price>0?'':'0より大きい商品価格を入力してください。';
    if(!(price>0)){ $('#priceUsd').focus(); return; }
    if(!(weight>0)){ showToast('判定に使う重量を入力してください'); return; }
    storageSet('filmCameraExchangeRate',String(rate));
    const result=choosePolicy(weight,price,rate),product=selectedItem?.name || $('#productSearch').value.trim() || '商品名未入力';
    $('#resultEmpty').hidden=true;$('#resultContent').hidden=false;
    $('#resultProduct').textContent=product;$('#resultWeight').textContent=fmtG(weight);$('#resultPrice').textContent=`${fmtUsd(price)}（${fmtYen(price*rate)}）`;
    $('#rateCaption').textContent=`1 USD = ${fmtNum(rate,2)}円`;
    $('#resultWarning').hidden=true;$('#resultManual').hidden=true;
    if(result.manual){
      $('#resultStatus').textContent='個別確認';$('#resultStatus').className='status manual';
      $('#policyName').textContent='V2ポリシー対象外';$('#usOverride').textContent='—';$('#resultWeightTier').textContent='2000g超';$('#resultPriceTier').textContent='—';$('#resultRateTable').textContent='—';
      $('#shippingCards').innerHTML='';
      $('#resultManual').textContent='重量が2000gを超えています。CPaSS実見積もりと配送サービスを個別に確認してください。';$('#resultManual').hidden=false;
    }else{
      const tier=result.tier;
      $('#resultStatus').textContent='判定完了';$('#resultStatus').className='status ready';$('#policyName').textContent=result.name;$('#usOverride').textContent=fmtUsd(result.usOverride);
      $('#resultWeightTier').textContent=tier.label;$('#resultPriceTier').textContent=`${tier.cpassTierG}g区分`;$('#resultRateTable').textContent=tier.rateTableName;
      const cards=[
        ['米国',result.usOverride,'出品単位で上書き',true],
        ['中国・韓国・台湾',tier.chinaKoreaTaiwan,'国際エアパケット',false],
        ['その他アジア',tier.otherAsia,'国際エアパケット',false],
        ['カナダ・英国・豪州など',tier.zone3,'非EU欧州・中東を含む',false],
        ['EU加盟国',tier.eu,'国際エアパケット・DDU',false],
        ['中南米・アフリカ',tier.zone5,'国際エアパケット',false]
      ];
      $('#shippingCards').innerHTML=cards.map(([label,usd,note,primary])=>`<div class="shipping-card ${primary?'primary':''}"><span>${label}</span><strong>${fmtUsd(usd)}</strong><small>${fmtYen(usd*rate)} · ${note}</small></div>`).join('');
      const warnings=[];
      const remain=tier.maxWeight-weight;if(remain>=0&&remain<=20){const next=DB.policies.tiers[DB.policies.tiers.indexOf(tier)+1];if(next)warnings.push(`上限まで残り${fmtG(remain)}です。計量誤差がある場合は${next.policyName}が安全です。`)}
      const weightMode=$('input[name="weightMode"]:checked').value;
      if(weightMode!=='measured') warnings.push('推定重量による仮判定です。出品・発送前に梱包後重量を実測してください。');
      if(tier.cpassTierG>DB.policies.model.validatedMaxTierG) warnings.push('1kg超の米国送料モデルは追加見積もり推奨区分です。高額・大型商品はCPaSSで照合してください。');
      if(price>250) warnings.push('250USD超の商品です。補償上限・関税・署名要否も個別に確認してください。');
      warnings.push('EU向けは日本郵便 国際エアパケットのDDUです。関税・現地通関手数料が購入者へ請求される可能性があります。150ユーロ以下でeBayがVATを徴収した注文は、発送時にIOSS番号を正確に入力してください。');
      if(tier.additionalItem>0) warnings.push(`複数在庫では、同一商品ごとの追加送料${fmtUsd(tier.additionalItem)}が設定されています。`);
      if(weightMode!=='measured' && selectedItem?.dataType==='genre-estimate'&&!localFor(selectedItem)) {
        warnings.push('この商品の個別重量は未収録のため、同ジャンルの上限寄りで計算しています。');
        const low=Number(selectedItem.weightMinG||0)+Number(selectedItem.packingMinG||0)+extraWeight();
        const high=Number(selectedItem.weightMaxG||0)+Number(selectedItem.packingMaxG||0)+extraWeight();
        const lowTier=DB.policies.tiers.find(t=>low<=t.maxWeight), highTier=DB.policies.tiers.find(t=>high<=t.maxWeight);
        if(lowTier && highTier && lowTier.code!==highTier.code) warnings.push(`推定範囲では${lowTier.policyName}〜${highTier.policyName}にまたがるため、現在は安全側の${highTier.policyName}で判定しています。`);
      }
      if(warnings.length){$('#resultWarning').textContent=warnings.join(' ');$('#resultWarning').hidden=false;}
    }
    requestAnimationFrame(()=>{if(innerWidth<1000)$('#resultPanel').scrollIntoView({behavior:'smooth',block:'start'})});
  }

  function renderDatasetSummary(){
    const m=DB.meta;$('#datasetSummary').innerHTML=[['収録商品',`${fmtNum(m.recordCount)}件`],['参考重量あり',`${fmtNum(m.referenceCount)}件`],['アクセサリー',`${fmtNum(m.accessoryCount)}件`],['ジャンル',`${fmtNum(m.genreCount)}分類`]].map(([l,v])=>`<div class="summary-stat"><strong>${v}</strong><span>${l}</span></div>`).join('');
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
    $('#dialogContent').innerHTML=`<div class="dialog-body"><span class="item-brand">${escapeHtml(item.brand)} · ${escapeHtml(typeLabel(item.kind))}</span><h2>${escapeHtml(item.name)}</h2><div class="selected-meta"><span class="tag">${escapeHtml(item.genreJa)}</span>${item.format?`<span class="tag">${escapeHtml(item.format)}</span>`:''}${item.mount?`<span class="tag">${escapeHtml(item.mount)}</span>`:''}<span class="quality-badge ${q.cls}">${escapeHtml(q.text)}</span></div><div class="dialog-weight"><div><span>${w.type==='estimate'?'推定重量範囲':'本体・商品重量'}</span><strong>${escapeHtml(itemWeightText(item))}</strong></div><div><span>安全側の推定梱包後重量</span><strong>${fmtG(w.value+(item.packingDefaultG??item.packingMaxG))}</strong></div></div><dl class="detail-list"><div><dt>重量条件</dt><dd>${escapeHtml(local?.note||item.weightCondition||'—')}</dd></div><div><dt>梱包材の目安</dt><dd>+${fmtG(item.packingMinG)}〜${fmtG(item.packingMaxG)}（標準 ${fmtG(item.packingDefaultG??item.packingMaxG)}）</dd></div><div><dt>マウント</dt><dd>${escapeHtml(item.mount||'—')}</dd></div><div><dt>フォーカス</dt><dd>${escapeHtml(item.focus||'—')}</dd></div><div><dt>レンズ方式</dt><dd>${escapeHtml(item.lensType||'—')}</dd></div><div><dt>発売年</dt><dd>${item.year||'—'}</dd></div><div><dt>同ジャンル登録数</dt><dd>${g?.count||0}件（参考重量 ${g?.referenceCount||0}件）</dd></div><div><dt>データ品質</dt><dd>${escapeHtml(q.text)}</dd></div></dl>${item.dataType==='genre-estimate'?`<div class="warning-box">この機種の個別重量は未確認です。${escapeHtml(item.genreJa)}の既知データから${fmtG(item.weightMinG)}〜${fmtG(item.weightMaxG)}と推定しています。</div>`:''}${similarHtml}<div class="dialog-actions"><button type="button" class="use-item">配送判定に使う</button><button type="button" class="browse-genre">同ジャンルを見る</button></div></div>`;
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
  $('#useGenreEstimate').addEventListener('click',()=>{const g=genreMap.get($('#genreEstimateSelect').value);if(!g)return;const name=$('#unknownProductName').value.trim()||`未登録の${g.genreJa}`;const item={id:`custom-${Date.now()}`,kind:'camera',brand:'未登録',name,aliases:[],genre:g.genre,genreJa:g.genreJa,format:'',focus:'',lensType:'',mount:'',year:null,weightG:null,weightMinG:g.typicalLowG,weightMaxG:g.typicalHighG,weightCondition:'同ジャンルの参考機種から推定',dataType:'genre-estimate',confidence:'D',packingProfile:'compact-standard',packingDefaultG:Math.round((g.packingMinG+g.packingMaxG)/2),packingMinG:g.packingMinG,packingMaxG:g.packingMaxG,searchText:name};selectItem(item);setView('judge');showToast('ジャンル推定を判定欄へ反映しました')});

  function selectLocalItem(item){localSelectedItem=item;$('#localProductSearch').value=item.name;$('#localGenre').value=item.genre;const w=effectiveWeight(item);if(w.type!=='estimate')$('#localBareWeight').value=w.value;$('#localSuggestions').hidden=true;}
  function renderLocalData(){
    $('#localCount').textContent=`${localMeasurements.length}件`;
    $('#localList').innerHTML=localMeasurements.length?localMeasurements.map(x=>`<div class="local-entry"><div><h3>${escapeHtml(x.name)}</h3><p>${x.bareWeight?`本体 ${fmtG(x.bareWeight)}`:''}${x.bareWeight&&x.packedWeight?' ／ ':''}${x.packedWeight?`梱包後 ${fmtG(x.packedWeight)}`:''} · ${escapeHtml(genreMap.get(x.genre)?.genreJa||x.genre||'未分類')}</p>${x.note?`<p>${escapeHtml(x.note)}</p>`:''}</div><button type="button" data-delete-local="${escapeHtml(x.id)}">削除</button></div>`).join(''):'<p class="empty-state-small">まだ保存された実測値はありません。</p>';
    $$('[data-delete-local]').forEach(b=>b.addEventListener('click',()=>{localMeasurements=localMeasurements.filter(x=>x.id!==b.dataset.deleteLocal);saveLocal();renderLocalData();renderDatabase();showToast('実測値を削除しました')}));
    $('#sourceList').innerHTML=DB.sources.map(s=>`<div class="source-row"><strong>${s.url?`<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.label)}</a>`:escapeHtml(s.label)}</strong><small>${escapeHtml(s.note)}</small></div>`).join('');
  }
  function updateLocalDerivedPacking(){const bare=Number($('#localBareWeight').value)||0,packed=Number($('#localPackedWeight').value)||0;const el=$('#localDerivedPacking');if(bare>0&&packed>bare){el.textContent=`梱包材の実測：${fmtG(packed-bare)}（梱包後−本体）`;el.classList.add('ready')}else{el.textContent='本体重量と梱包後重量を入力すると、梱包材重量を自動計算します。';el.classList.remove('ready')}}
  ['localBareWeight','localPackedWeight'].forEach(id=>$('#'+id).addEventListener('input',updateLocalDerivedPacking));
  $('#localForm').addEventListener('submit',e=>{
    e.preventDefault();const name=$('#localProductSearch').value.trim(),bare=Number($('#localBareWeight').value)||null,packed=Number($('#localPackedWeight').value)||null;
    if(!name||(!bare&&!packed)){showToast('商品名と、どちらかの重量を入力してください');return;}
    const entry={id:`local-${Date.now()}`,itemId:localSelectedItem?.id||null,name,brand:localSelectedItem?.brand||'',genre:$('#localGenre').value,bareWeight:bare,packedWeight:packed,packingWeight:(bare&&packed&&packed>bare)?packed-bare:null,note:$('#localNote').value.trim(),updatedAt:new Date().toISOString()};
    localMeasurements=localMeasurements.filter(x=>!(entry.itemId&&x.itemId===entry.itemId)&&normalize(x.name)!==normalize(entry.name));localMeasurements.unshift(entry);saveLocal();
    e.target.reset();localSelectedItem=null;updateLocalDerivedPacking();renderLocalData();renderDatabase();showToast('実測値を保存しました');
  });
  $('#exportLocal').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({version:1,measurements:localMeasurements},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='film-camera-measurements.json';a.click();URL.revokeObjectURL(a.href)});
  $('#importLocal').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{const data=JSON.parse(await file.text());const rows=Array.isArray(data)?data:data.measurements;if(!Array.isArray(rows))throw new Error();localMeasurements=rows;saveLocal();renderLocalData();showToast('実測データを読み込みました')}catch{showToast('JSONファイルを読み込めませんでした')}e.target.value=''});

  function initSearches(){
    const product=$('#productSearch'),suggestions=$('#searchSuggestions');product.addEventListener('input',debounce(()=>renderSuggestions(suggestions,product.value,selectItem)));product.addEventListener('focus',()=>renderSuggestions(suggestions,product.value,selectItem));
    const local=$('#localProductSearch'),ls=$('#localSuggestions');local.addEventListener('input',debounce(()=>{localSelectedItem=null;renderSuggestions(ls,local.value,selectLocalItem)}));local.addEventListener('focus',()=>renderSuggestions(ls,local.value,selectLocalItem));
    document.addEventListener('click',e=>{if(!$('#judgeSearchBox').contains(e.target))suggestions.hidden=true;if(!$('#localForm').contains(e.target))ls.hidden=true});
  }

  function init(){
    initTheme();populateFilters();$('#packingProfile').insertAdjacentHTML('beforeend',(DB.packingProfiles||[]).map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.label)}（${p.defaultG}g）</option>`).join(''));renderExtraPresets();renderPackingBreakdown();$('#clearExtras').addEventListener('click',()=>{$$('[data-extra-check]').forEach(x=>x.checked=false);$('#customExtra').value=0;updateCalculatedWeight()});renderDatasetSummary();renderCoverage();initSearches();renderGenres();renderLocalData();
    const savedRate=Number(storageGet('filmCameraExchangeRate'));if(savedRate>0)$('#exchangeRate').value=savedRate;
    $('#judgeForm').addEventListener('submit',judge);$('#copyPolicy').addEventListener('click',async()=>{const t=$('#policyName').textContent;if(!t||t==='V2ポリシー対象外')return;try{await navigator.clipboard.writeText(t)}catch{const ta=document.createElement('textarea');ta.value=t;document.body.append(ta);ta.select();document.execCommand('copy');ta.remove()}showToast('ポリシー名をコピーしました')});$('#copyUsOverride').addEventListener('click',async()=>{const t=$('#usOverride').textContent.replace('$','');if(!t||t==='—')return;try{await navigator.clipboard.writeText(t)}catch{const ta=document.createElement('textarea');ta.value=t;document.body.append(ta);ta.select();document.execCommand('copy');ta.remove()}showToast('米国送料をコピーしました')});
    const initial=(location.hash||'#judge').slice(1);if(['judge','database','genres','data'].includes(initial))setView(initial);
    updateCalculatedWeight();renderDatabase();
  }
  init();
})();
