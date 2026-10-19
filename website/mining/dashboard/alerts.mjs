// Session-only observation monitor; no addresses, persistence or requests.
export function validateAlertSettings(settings) {
 if(!settings || !Number.isFinite(settings.hashDropPercent) || settings.hashDropPercent<1 || settings.hashDropPercent>100
   || !Number.isSafeInteger(settings.minimumWorkers) || settings.minimumWorkers<0 || settings.minimumWorkers>1000)
  throw new Error('Use a hashrate drop of 1–100% and a minimum of 0–1000 workers.');
 return {hashDropPercent:settings.hashDropPercent,minimumWorkers:settings.minimumWorkers};
}
export function createAlertMonitor(settings) {
 const config=validateAlertSettings(settings);
 let baseline=null,lastTime=-Infinity,lastObservation=0;
 const conditions=new Map();
 function observe(kind,active,now,message,events,countable) {
  const state=conditions.get(kind)||{count:0,latched:false,lastAlert:-Infinity};
  if(active===null){state.count=0;} // Unknown breaks consecutive samples, not an alert latch.
  else if(!active){state.count=0;state.latched=false;}
  else if(countable) {
   state.count++;
   if(state.count>=2&&!state.latched&&now-state.lastAlert>=600000){
    events.push({kind,message});state.latched=true;state.lastAlert=now;
   }
  }
  conditions.set(kind,state);
 }
 return {
  sample(data,now) {
   // Caller supplies monotonic milliseconds. Rapid clicks cannot satisfy persistence.
   if(!Number.isFinite(now)||now<0||now<lastTime)return [];
   const countable=now-lastTime>=30000;
   if(data!==null&&(!Number.isSafeInteger(data.observed_at)||data.observed_at<=lastObservation))return [];
   if(now-lastTime>90000||(data!==null&&lastObservation>0&&data.observed_at-lastObservation>90))for(const state of conditions.values())state.count=0;
   if(countable)lastTime=now;const events=[];
   observe('lookup',data===null,now,'Repeated pool lookups failed. This does not prove the pool or your miner is offline.',events,countable);
   if(data===null){for(const kind of ['hashrate','workers']){const s=conditions.get(kind);if(s)s.count=0;}return events;}
   lastObservation=data.observed_at;
   const hash=typeof data.hashrate_hps==='number'&&Number.isFinite(data.hashrate_hps)&&data.hashrate_hps>=0?data.hashrate_hps:null;
   if(baseline===null&&hash!==null&&hash>0)baseline=hash;
   observe('hashrate',hash===null||baseline===null?null:hash<=baseline*(1-config.hashDropPercent/100),now,
    'Pool-reported ten-minute hashrate stayed below your session threshold. Check the dashboard; this is not an instantaneous CPU reading.',events,countable);
   const count=Number.isSafeInteger(data.active_workers)&&data.active_workers>=0?data.active_workers:null;
   observe('workers',count===null?null:count<config.minimumWorkers,now,
    'The pool reported fewer connected workers than your minimum on consecutive observations. This does not identify a particular offline machine.',events,countable);
   return events;
  },
  settings:()=>({...config}),
  baseline:()=>baseline
 };
}
