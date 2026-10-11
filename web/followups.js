/* Collection actions are private to the operator workspace. */
function collectionTrackButton(action) {
  const existing=(state.followups||[]).some(f=>f.floor_id===action.floor_id);
  return action.kind==='collection'&&!existing?`<button class="btn light" data-track-collection="${esc(action.floor_id)}">${t('Track the collection fix','संग्रह सुधार पर नज़र रखें')}</button>`:'';
}

function followupsPanel() {
  const statuses={
    open:t('Fix not recorded','सुधार दर्ज नहीं'),
    awaiting_checks:t('More checks needed','और निरीक्षण चाहिए'),
    mixing_observed:t('Mixing still observed','मिलावट अभी भी दिखी'),
    ready_for_review:t('Ready for operator review','समीक्षा के लिए तैयार'),
    reviewed:t('Evidence reviewed','साक्ष्य की समीक्षा हुई'),
    review_needed:t('Review needed again','दोबारा समीक्षा चाहिए')
  };
  return `<section class="section-gap" aria-labelledby="collection-actions-title"><h2 id="collection-actions-title">${t('Collection actions — current status','संग्रह सुधार — वर्तमान स्थिति')}</h2><p class="plan-evidence">${t('Saved across weeks. This section uses all checks through today, independently of the week selected above. Demo actions use simulated data.','हर सप्ताह सुरक्षित। यह भाग ऊपर चुने सप्ताह से स्वतंत्र, आज तक के सभी निरीक्षण उपयोग करता है। डेमो के आँकड़े काल्पनिक हैं।')}</p><div class="tip-box"><p>${t('A recorded fix starts follow-up from the next calendar day. Review needs separation observed on 3 distinct days, no mixing since the fix, and a separated check within the past 7 days. Unknown observations never count as success. This is a follow-up checklist, not proof of impact.','दर्ज सुधार के अगले दिन से निरीक्षण गिने जाते हैं। समीक्षा के लिए 3 अलग दिनों में अलग संग्रह, सुधार के बाद कोई मिलावट नहीं, और पिछले 7 दिनों में अलग संग्रह का निरीक्षण चाहिए। अज्ञात को सफलता नहीं मानते। यह अनुवर्ती सूची है, प्रभाव का प्रमाण नहीं।')}</p></div>
    ${(state.followups||[]).length?`<div class="plan-grid section-gap">${state.followups.map(f=>{
      const fix=f.intervention;
      return `<article class="panel collection-case" data-case="${esc(f.id)}"><div class="panel-head"><h3>${esc(f.name)}</h3><span class="pill ${f.status==='reviewed'?'':f.status==='mixing_observed'||f.status==='review_needed'?'red':'amber'}">${statuses[f.status]}</span></div>
      <p class="plan-evidence">${t('Mixing first tracked from','दर्ज मिलावट का दिन')}: ${esc(f.baseline.date)} · ${f.source==='simulated'?t('Demo','डेमो'):t('Pilot','पायलट')}</p>
      ${fix?`<p class="collection-note">${esc(fix.note)}</p><p>${esc(fix.owner_role)} · ${t('Fix','सुधार')}: ${esc(fix.date)} · ${t('Review due','समीक्षा तिथि')}: ${esc(fix.due_date)} ${f.overdue?`<strong class="pill amber">${t('Overdue','विलंबित')}</strong>`:''}</p>`:`<p>${t('Record what was changed before evaluating the follow-up. Use a team role, without resident names.','अनुवर्ती समीक्षा से पहले किया गया सुधार दर्ज करें। निवासी के नाम के बिना टीम की भूमिका लिखें।')}</p>`}
      <dl class="collection-counts"><div><dt>${t('Separated days','अलग संग्रह वाले दिन')}</dt><dd>${f.separated_days} / ${f.required_days}</dd></div><div><dt>${t('Mixed checks','मिलावट निरीक्षण')}</dt><dd>${f.mixed_checks}</dd></div><div><dt>${t('Unknown checks','अज्ञात निरीक्षण')}</dt><dd>${f.unknown_checks}</dd></div></dl>
      ${fix&&!f.fresh?`<p class="plan-evidence">${t('No confirmed separated collection in the past 7 days. Record a current observation.','पिछले 7 दिनों में अलग संग्रह की पुष्टि नहीं। वर्तमान निरीक्षण दर्ज करें।')}</p>`:''}
      ${f.status==='review_needed'?`<p role="status">${t('The previous review no longer covers the current evidence. Inspect changes below; record a new fix if mixing continues.','पिछली समीक्षा वर्तमान साक्ष्य पर लागू नहीं। नीचे बदलाव देखें; मिलावट जारी हो तो नया सुधार दर्ज करें।')}</p>`:''}
      <div class="collection-controls"><button class="btn light" data-record-fix="${esc(f.id)}">${fix?t('Record another fix','अगला सुधार दर्ज करें'):t('Record the fix','सुधार दर्ज करें')}</button>${f.can_review?`<button class="btn" data-review-fix="${esc(f.id)}">${t('Review evidence','साक्ष्य की समीक्षा')}</button>`:''}<button class="text-btn" data-followup="${esc(f.floor_id)}">${t('Record next check','अगला निरीक्षण दर्ज करें')}</button></div>
      <details class="collection-evidence"><summary>${t('Observation evidence','निरीक्षण साक्ष्य')} (${f.evidence.length})</summary><p>${f.separated_checks} ${t('separated observations; repeated rounds on one day count as one day.','अलग संग्रह निरीक्षण; एक दिन के कई निरीक्षण एक दिन गिने जाते हैं।')}</p>${f.evidence.length?`<ul>${f.evidence.map(e=>`<li>${esc(e.date)} · ${esc(roundLabel(e.round))} · <strong>${e.kept_separate===false?t('Mixed','मिला हुआ'):e.kept_separate===true&&e.human_confirmed?t('Kept separate','अलग रखा'):t('Unknown','अज्ञात')}</strong> · ${e.reporter==='worker'?t('Worker','कर्मचारी'):t('Operator','संचालक')}</li>`).join('')}</ul>`:`<p>${t('No checks after the fix yet. Same-day checks are excluded.','सुधार के बाद निरीक्षण नहीं। उसी दिन के निरीक्षण नहीं गिने जाते।')}</p>`}</details>
      <details class="collection-evidence"><summary>${t('Action history','सुधार का इतिहास')} (${f.history.length})</summary><ol>${f.history.map(h=>`<li>${esc(new Date(h.at).toLocaleString(state.lang==='hi'?'hi-IN':'en-IN'))} · ${h.event==='opened'?t('Action opened','सुधार शुरू'):h.event==='reviewed'?t('Evidence reviewed','साक्ष्य की समीक्षा'):t('Fix recorded','सुधार दर्ज')}${h.note?`<p class="collection-note">${esc(h.note)} · ${esc(h.owner_role)} · ${esc(h.date)}</p>`:''}</li>`).join('')}</ol></details></article>`;
    }).join('')}</div>`:`<p class="plan-evidence section-gap">${t('No collection actions tracked yet. Start from a collection mixing recommendation above.','अभी कोई संग्रह सुधार दर्ज नहीं। ऊपर मिलावट की सलाह से शुरू करें।')}</p>`}</section>`;
}

function openFixForm(record) {
  const modal=$('#modal'), workspace=state.workspace;
  const earliest=record.intervention?.date||record.baseline.date;
  modal.innerHTML=`<h2>${t('Record a collection fix','संग्रह सुधार दर्ज करें')}</h2><p>${t('Describe a change already made. Checks from the next day will be used. A new fix starts a new review period; earlier attempts stay in the history.','किए गए बदलाव का विवरण दें। अगले दिन से निरीक्षण गिने जाएँगे। नया सुधार समीक्षा अवधि फिर शुरू करता है; पहले के प्रयास इतिहास में रहते हैं।')}</p><form id="collection-fix-form"><label class="field">${t('Fix date','सुधार की तारीख')}<input name="date" type="date" min="${esc(earliest)}" max="${esc(state.health.today)}" value="${esc(state.health.today)}" required></label><label class="field">${t('Responsible role (no personal names)','ज़िम्मेदार भूमिका (व्यक्तिगत नाम नहीं)')}<input name="owner_role" maxlength="80" placeholder="${t('Collection coordinator','संग्रह समन्वयक')}" required></label><label class="field">${t('What changed?','क्या बदलाव किया?')}<textarea name="note" maxlength="500" rows="3" required></textarea></label><label class="field">${t('Review due','समीक्षा की तारीख')}<input name="due_date" type="date" min="${esc(earliest)}" value="${esc(state.health.today)}" required></label><p id="collection-form-error" role="alert"></p><div class="collection-controls"><button class="btn" type="submit">${t('Save fix','सुधार सहेजें')}</button><button class="btn light" type="button" id="cancel-collection-fix">${t('Cancel','रद्द करें')}</button></div></form>`;
  modal.showModal();
  $('#cancel-collection-fix').onclick=()=>modal.close();
  $('#collection-fix-form').onsubmit=async event=>{
    event.preventDefault();const button=event.target.querySelector('[type=submit]');button.disabled=true;
    const data=Object.fromEntries(new FormData(event.target));
    try{
      await api(`/api/${workspace}/followups/${encodeURIComponent(record.id)}/intervention`,{method:'PUT',body:JSON.stringify({...data,revision:record.revision})});
      modal.close();await render();toast(t('Fix saved. Follow-up evidence starts the next day.','सुधार सुरक्षित। अगले दिन से निरीक्षण गिने जाएँगे।'));
    }catch(error){$('#collection-form-error').textContent=error.message;button.disabled=false;}
  };
}

document.addEventListener('click',async event=>{
  const target=event.target.closest('[data-track-collection],[data-record-fix],[data-review-fix]');
  if(!target)return;
  event.preventDefault();target.disabled=true;
  try {
    if(target.dataset.trackCollection){
      await api(endpoint('followups'),{method:'POST',body:JSON.stringify({floor_id:target.dataset.trackCollection})});
      await render();document.getElementById('collection-actions-title')?.scrollIntoView({block:'start'});
      return;
    }
    const record=(state.followups||[]).find(f=>f.id===(target.dataset.recordFix||target.dataset.reviewFix));
    if(!record){await render();return;}
    if(target.dataset.recordFix){openFixForm(record);return;}
    const workspace=state.workspace;
    const confirmed=await confirmAction(t('Review this collection evidence?','इस संग्रह साक्ष्य की समीक्षा करें?'),t(`You have ${record.separated_days} distinct separated days, ${record.unknown_checks} unknown checks and no recorded mixing after the fix. Confirm you inspected the evidence. This does not prove lasting improvement.`,`${record.separated_days} अलग दिनों में अलग संग्रह, ${record.unknown_checks} अज्ञात निरीक्षण और सुधार के बाद कोई दर्ज मिलावट नहीं। साक्ष्य देखने की पुष्टि करें। यह स्थायी सुधार का प्रमाण नहीं है।`),t('Confirm review','समीक्षा की पुष्टि'));
    if(confirmed){await api(`/api/${workspace}/followups/${encodeURIComponent(record.id)}/review`,{method:'POST',body:JSON.stringify({revision:record.revision,evidence_signature:record.evidence_signature,human_confirmed:true})});await render();toast(t('Evidence review saved.','साक्ष्य समीक्षा सुरक्षित।'));}
  } catch(error){toast(error.message);if(error.status===409)await render();}
  finally{target.disabled=false;}
});
