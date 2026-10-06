import React from 'react';
import clsx from 'clsx';
import {translate} from '@docusaurus/Translate';
import {useAnchorTargetClassName} from '@docusaurus/theme-common';
import Link from '@docusaurus/Link';
import useBrokenLinks from '@docusaurus/useBrokenLinks';
import './styles.module.css';

export default function Heading({
  as: As,
  id,
  'data-bee-title-anchor': titleAnchor,
  ...props
}) {
  const brokenLinks = useBrokenLinks();
  const anchorTargetClassName = useAnchorTargetClassName(id);
  const isAnchoredTitle = As === 'h1' && titleAnchor;

  if ((As === 'h1' && !isAnchoredTitle) || !id) {
    return <As {...props} id={undefined} />;
  }

  brokenLinks.collectAnchor(id);
  const anchorTitle = translate(
    {
      id: 'theme.common.headingLinkTitle',
      message: 'Direct link to {heading}',
      description: 'Title for link to heading',
    },
    {
      heading: typeof props.children === 'string' ? props.children : id,
    },
  );

  return (
    <As
      {...props}
      className={clsx('anchor', anchorTargetClassName, props.className)}
      id={id}>
      {props.children}
      <Link
        className="hash-link"
        to={`#${id}`}
        aria-label={anchorTitle}
        title={anchorTitle}
        translate="no">
        &#8203;
      </Link>
    </As>
  );
}
