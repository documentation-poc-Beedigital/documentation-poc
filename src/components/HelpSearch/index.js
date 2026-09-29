import React from 'react';
import HelpIcon from '@site/src/components/HelpIcon';

export default function HelpSearch() {
  function openSearch() {
    // Use the navbar's search so the same local index and dialog serve both entry points.
    const search = document.querySelector('.navbar .aa-DetachedSearchButton, .navbar .aa-Input');
    if (search instanceof HTMLButtonElement) search.click();
    else search?.focus();
  }

  return (
    <button className="button button--primary help-search" onClick={openSearch}>
      <HelpIcon name="search" /> Buscar en el Centro de Ayuda
    </button>
  );
}
