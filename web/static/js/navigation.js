/**
 * 공통 네비게이션 컴포넌트
 */

function renderNavigation(activePage) {
    const nav = document.querySelector('.navigation');
    if (!nav) return;

    const pages = [
        { id: 'dashboard', href: 'dashboard.html', label: '대시보드' },
        { id: 'trends', href: 'trends.html', label: '추이 분석' },
        { id: 'history', href: 'history.html', label: '히스토리' }
    ];

    nav.innerHTML = pages.map(page => {
        const activeClass = page.id === activePage ? ' class="active"' : '';
        return `<a href="${page.href}"${activeClass}>${page.label}</a>`;
    }).join('');
}
