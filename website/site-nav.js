// Static links work without JavaScript; enhance with an accessible disclosure.
(function () {
  'use strict';
  const header=document.querySelector('.site-header');
  const button=header?.querySelector('.menu-toggle');
  const nav=document.getElementById('site-nav');
  if(!header||!button||!nav)return;
  function close(restoreFocus=false){nav.hidden=true;button.setAttribute('aria-expanded','false');if(restoreFocus)button.focus();}
  header.classList.add('navigation-ready');close();
  button.addEventListener('click',()=>{const open=nav.hidden;nav.hidden=!open;button.setAttribute('aria-expanded',String(open));});
  nav.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>close()));
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!nav.hidden){event.preventDefault();close(true);}});
  document.addEventListener('click',event=>{if(!header.contains(event.target))close();});
  header.addEventListener('focusout',event=>{if(!header.contains(event.relatedTarget))close();});
})();
