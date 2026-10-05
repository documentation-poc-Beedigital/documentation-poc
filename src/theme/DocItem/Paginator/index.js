import React from 'react';
import {ArrowLeftIcon, ArrowRightIcon} from '@heroicons/react/24/outline';
import Translate, {translate} from '@docusaurus/Translate';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import BeeButton from '@site/src/components/BeeButton';

function PaginationLink({direction, item}) {
  const isNext = direction === 'next';
  const label = isNext ? (
    <Translate
      id="theme.docs.paginator.next"
      description="The label used to navigate to the next doc">
      Siguiente
    </Translate>
  ) : (
    <Translate
      id="theme.docs.paginator.previous"
      description="The label used to navigate to the previous doc">
      Anterior
    </Translate>
  );

  return (
    <BeeButton
      aria-label={`${isNext ? 'Ir al artículo siguiente' : 'Ir al artículo anterior'}: ${item.title}`}
      className={`bee-pagination__link bee-pagination__link--${direction}`}
      href={item.permalink}
      leadingIcon={isNext ? undefined : ArrowLeftIcon}
      size="small"
      trailingIcon={isNext ? ArrowRightIcon : undefined}
      variant={isNext ? 'secondary' : 'tertiary'}>
      <span>{label}</span>
    </BeeButton>
  );
}

export default function DocItemPaginator() {
  const {metadata} = useDoc();
  const {previous, next} = metadata;

  if (!previous && !next) return null;

  return (
    <nav
      aria-label={translate({
        id: 'theme.docs.paginator.navAriaLabel',
        message: 'Docs pages',
        description: 'The ARIA label for the docs pagination',
      })}
      className="bee-pagination">
      {previous && <PaginationLink direction="previous" item={previous} />}
      {next && <PaginationLink direction="next" item={next} />}
    </nav>
  );
}
