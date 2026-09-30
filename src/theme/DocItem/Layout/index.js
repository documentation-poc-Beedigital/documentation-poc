import React from 'react';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import DocItemContent from '@theme/DocItem/Content';
import DocItemFooter from '@theme/DocItem/Footer';
import DocItemPaginator from '@theme/DocItem/Paginator';
import DocBreadcrumbs from '@theme/DocBreadcrumbs';
import ContentVisibility from '@theme/ContentVisibility';
import DocVersionBadge from '@theme/DocVersionBadge';
import DocVersionBanner from '@theme/DocVersionBanner';

// The article H1 and breadcrumb already identify the current page. Omitting the
// generated TOC prevents Docusaurus from repeating that title in a right column.
export default function DocItemLayout({children}) {
  const {metadata} = useDoc();

  return (
    <div className="row">
      <div className="col">
        <ContentVisibility metadata={metadata} />
        <DocVersionBanner />
        <div className="bee-doc-item-container">
          <article>
            <DocBreadcrumbs />
            <DocVersionBadge />
            <DocItemContent>{children}</DocItemContent>
            <DocItemFooter />
          </article>
          <DocItemPaginator />
        </div>
      </div>
    </div>
  );
}
