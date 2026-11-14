// Extracción usada para el Evidence Board (Datostada MX 2026).
// Ejecutar en la consola del navegador estando en una página de www.gob.mx (mismo origen que el archivo).
// Lee el XLSX oficial de CONAGUA sin librerías (ZIP + XML), filtra Yucatán y devuelve el CSV del extracto
// (separador ';'), además de las sumas de control que verifica scripts/analisis.py.
const URL_P = 'https://www.gob.mx/cms/uploads/attachment/file/1084131/Calidad_del_Agua_Subterr_nea_p_2012-2025.xlsx';
const URL_A = 'https://www.gob.mx/cms/uploads/attachment/file/1084130/Calidad_del_Agua_Subterr_nea_a_2025.xlsx';
async function loadXlsx(url){
  const buf=await fetch(url).then(r=>r.arrayBuffer()); const dv=new DataView(buf); const u8=new Uint8Array(buf);
  let eocd=-1; for(let i=u8.length-22;i>=0;i--){ if(dv.getUint32(i,true)===0x06054b50){eocd=i;break;} }
  const n=dv.getUint16(eocd+10,true); let off=dv.getUint32(eocd+16,true); const E={};
  for(let k=0;k<n;k++){ const method=dv.getUint16(off+10,true), csize=dv.getUint32(off+20,true), fnl=dv.getUint16(off+28,true),
    exl=dv.getUint16(off+30,true), cml=dv.getUint16(off+32,true), lho=dv.getUint32(off+42,true);
    const name=new TextDecoder().decode(u8.slice(off+46,off+46+fnl)); E[name]={method,csize,lho}; off+=46+fnl+exl+cml; }
  async function rd(name){ const e=E[name]; const s=e.lho+30+dv.getUint16(e.lho+26,true)+dv.getUint16(e.lho+28,true); const d=u8.slice(s,s+e.csize);
    if(e.method===0) return new TextDecoder().decode(d);
    return await new Response(new Blob([d]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).text(); }
  const ssd=new DOMParser().parseFromString(await rd('xl/sharedStrings.xml'),'application/xml');
  const ss=[...ssd.getElementsByTagName('si')].map(si=>[...si.getElementsByTagName('t')].map(t=>t.textContent).join(''));
  const ci=ref=>{let n=0; for(const c of ref.match(/^[A-Z]+/)[0]) n=n*26+c.charCodeAt(0)-64; return n-1;};
  const d=new DOMParser().parseFromString(await rd('xl/worksheets/sheet1.xml'),'application/xml'); const rows=[];
  for(const r of d.getElementsByTagName('row')){ const a=[]; for(const c of r.getElementsByTagName('c')){ const t=c.getAttribute('t'), v=c.getElementsByTagName('v')[0];
    a[ci(c.getAttribute('r'))]= t==='s'?ss[+v.textContent]:(v?v.textContent:null);} rows.push(a);} return rows; }

const rows = await loadXlsx(URL_P);            // fila 0 = encabezados; una fila por sitio, PERIODO = '2012-2025'
const yuc = rows.slice(1).filter(r=>/YUCAT/i.test(r[3]||''));
const f=(v,d)=>{ if(v==null) return ''; if(/^</.test(v)) return v; const x=parseFloat(v); return isNaN(x)?v:(+x.toFixed(d)).toString(); };
const lines=['clave;sitio;municipio;subtipo;lat;lon;cond_uScm;sdt_mgL;cal_sdt_salin;cf_nmp100;cal_cf;n_no3_mgL;cal_no3;semaforo;contaminantes'];
yuc.forEach(r=>lines.push([r[0],r[1],r[4],r[6],f(r[7],4),f(r[8],4),f(r[12],0),f(r[14],0),r[16]||'',f(r[21],1),r[22]||'',f(r[23],2),r[24]||'',r[39]||'',(r[40]||'').replace(/,\s*$/,'').trim()].join(';')));
const num=v=>{const x=parseFloat(v); return isNaN(x)?0:x;};
const control = { n: yuc.length, sumNO3: +yuc.reduce((a,r)=>a+ +(+num(r[23])).toFixed(2),0).toFixed(2),
  sumCond: yuc.reduce((a,r)=>a+Math.round(num(r[12])),0), sumSDT: yuc.reduce((a,r)=>a+Math.round(num(r[14])),0),
  semaforoNacional: rows.slice(1).reduce((a,r)=>(a[r[39]]=(a[r[39]]||0)+1,a),{}) };
const anual = await loadXlsx(URL_A);
control.sitiosYucatan2025 = anual.slice(1).filter(r=>/YUCAT/i.test(r[3]||'')).length;   // resultado: 0
({control, csv: lines.join('\n')})
