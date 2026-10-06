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

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!expanded || !root) {
      root?.style.removeProperty('--help-search-available-width');
      root?.style.removeProperty('--help-search-inline-offset');
      return undefined;
    }

    const fitToNavbar = () => {
      const documentWidth = document.documentElement.clientWidth;
      const navbar = root.closest('.navbar__inner');
      const navbarRect = navbar?.getBoundingClientRect();
      const leftItems = navbar?.querySelector('.navbar__items:not(.navbar__items--right)');
      const leftRect = leftItems?.getBoundingClientRect();
      const rightEdge = Math.min(navbarRect?.right ?? documentWidth, documentWidth);
      const leftEdge = Math.max(navbarRect?.left ?? 0, leftRect?.right ?? navbarRect?.left ?? 0);

      // Keep the local search end inside the useful document width. The
      // navbar can be laid out against the CSS viewport (including its
      // scrollbar), while clientWidth is the actual visible boundary.
      root.style.setProperty(
        '--help-search-available-width',
        `${Math.max(0, rightEdge - leftEdge)}px`,
      );
      root.style.setProperty('--help-search-inline-offset', '0px');
      const overflow = Math.max(0, root.getBoundingClientRect().right - rightEdge);
      root.style.setProperty('--help-search-inline-offset', `${overflow}px`);
    };

    fitToNavbar();
    window.addEventListener('resize', fitToNavbar);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(fitToNavbar);
    if (observer) observer.observe(root);
    return () => {
      window.removeEventListener('resize', fitToNavbar);
      observer?.disconnect();
    };
  }, [expanded]);

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
