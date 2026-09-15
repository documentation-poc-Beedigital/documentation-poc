import React from 'react';

export default function HelpSearch() {
  function openSearch() {
    // Use the navbar's search so the same local index and dialog serve both entry points.
    const search = document.querySelector('.navbar .aa-DetachedSearchButton, .navbar .aa-Input');
    if (search instanceof HTMLButtonElement) search.click();
    else search?.focus();
  }

  return (
    <button className="button button--primary help-search" onClick={openSearch}>
      <span aria-hidden="true">⌕</span> Buscar en el Centro de Ayuda
    </button>
  );
}
