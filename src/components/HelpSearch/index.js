import React from 'react';
import {MagnifyingGlassIcon} from '@heroicons/react/24/outline';
import BeeButton from '@site/src/components/BeeButton';

export default function HelpSearch() {
  function openSearch() {
    // Use the navbar's search so the same local index and dialog serve both entry points.
    const search = document.querySelector('.navbar .aa-DetachedSearchButton, .navbar .aa-Input');
    if (search instanceof HTMLButtonElement) search.click();
    else search?.focus();
  }

  return (
    <BeeButton className="help-search" leadingIcon={MagnifyingGlassIcon} onClick={openSearch}>
      Buscar en el Centro de Ayuda
    </BeeButton>
  );
}
