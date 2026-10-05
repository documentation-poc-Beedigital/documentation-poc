import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {MagnifyingGlassIcon, XMarkIcon} from '@heroicons/react/24/outline';
import OriginalSearchBar from '@theme-original/SearchBar';

export default function SearchBar() {
  const [expanded, setExpanded] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);

  // The local-search theme opts into Autocomplete's detached dialog with an
  // empty media query. Keep its index and result rendering, but make that one
  // query non-matching so Autocomplete renders its normal inline combobox.
  useLayoutEffect(() => {
    const nativeMatchMedia = window.matchMedia.bind(window);
    window.matchMedia = query => nativeMatchMedia(query === '' ? 'not all' : query);
    return () => {
      window.matchMedia = nativeMatchMedia;
    };
  }, []);

  useEffect(() => {
    if (!expanded) return undefined;
    const frame = window.requestAnimationFrame(() => {
      rootRef.current?.querySelector('.aa-Input')?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [expanded]);

  function closeSearch({restoreFocus = true} = {}) {
    const clear = rootRef.current?.querySelector('.aa-ClearButton');
    if (clear instanceof HTMLButtonElement) clear.click();
    setExpanded(false);
    if (restoreFocus) {
      window.requestAnimationFrame(() => triggerRef.current?.focus());
    }
  }

  function handleBlur(event) {
    if (!expanded || event.currentTarget.contains(event.relatedTarget)) return;
    const input = rootRef.current?.querySelector('.aa-Input');
    if (!input?.value) closeSearch({restoreFocus: false});
  }

  function handleKeyDown(event) {
    if (expanded && event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      closeSearch();
    }
  }

  return (
    <div
      className={`bee-navbar-search${expanded ? ' bee-navbar-search--expanded' : ''}`}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      ref={rootRef}>
      <button
        aria-expanded={expanded}
        aria-label="Abrir búsqueda"
        className="bee-navbar-search__trigger"
        onClick={() => setExpanded(true)}
        ref={triggerRef}
        type="button">
        <MagnifyingGlassIcon aria-hidden="true" focusable="false" />
        <span>Buscar…</span>
      </button>
      <div aria-hidden={!expanded} className="bee-navbar-search__field">
        <OriginalSearchBar />
      </div>
      {expanded && (
        <button
          aria-label="Cerrar búsqueda"
          className="bee-navbar-search__close"
          onClick={() => closeSearch()}
          type="button">
          <XMarkIcon aria-hidden="true" focusable="false" />
        </button>
      )}
    </div>
  );
}
