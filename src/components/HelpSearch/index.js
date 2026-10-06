import React from 'react';
import {MagnifyingGlassIcon} from '@heroicons/react/24/outline';
import BeeButton from '@site/src/components/BeeButton';

export default function HelpSearch() {
  function openSearch() {
    // Reuse the navbar search so both entry points share the local Docusaurus index.
    const trigger = document.querySelector('.navbar .bee-navbar-search__trigger');
    const input = document.querySelector('.navbar .aa-Input');
    if (trigger instanceof HTMLButtonElement) trigger.click();
    else input?.focus();
  }

  return (
    <BeeButton className="help-search" leadingIcon={MagnifyingGlassIcon} onClick={openSearch}>
      Buscar en el Centro de Ayuda
    </BeeButton>
  );
}
