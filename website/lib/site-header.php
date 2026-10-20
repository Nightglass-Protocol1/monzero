<?php
declare(strict_types=1);
// Site header for PHP-rendered pages: the owner's twelve links plus the submenus that
// utils/website/nav_submenus.py writes to lib/site-nav-submenus.json (same markup as static pages).
if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) { http_response_code(404); exit; }
require_once __DIR__ . '/auth.php';

const SITE_NAV_LINKS = [['/', 'Home'], ['/explorer/', 'Explorer'], ['/stats/', 'Stats'], ['/wallets/', 'Public wallets'], ['/app/', 'Studio'], ['/roadmap/', 'Roadmap'],
    ['/WHITEPAPER.md?rev=1.5-20261017', 'Whitepaper'], ['/#mine', 'Mining'], ['https://pool.monzero.org/', 'Pool'], ['/founder/', 'Founder'], ['/fund/', 'Donate'], ['/security/', 'Security']];

// $current: the path of this page, e.g. /faucet/ (marked aria-current in its submenu).
function siteHeader(string $current): string {
    $subs = json_decode((string)@file_get_contents(__DIR__ . '/site-nav-submenus.json'), true) ?: [];
    $nav = '';
    foreach (SITE_NAV_LINKS as [$href, $label]) {
        $top = '<a href="' . authH($href) . '">' . authH($label) . '</a>';
        if (empty($subs[$label])) { $nav .= $top; continue; }
        $id = 'nav-sub-' . trim((string)preg_replace('/[^a-z]+/', '-', strtolower($label)), '-');
        $here = in_array($current, array_column($subs[$label], 0), true);
        $items = implode('', array_map(fn($s) => '<a href="' . authH($s[0]) . '"' . ($s[0] === $current ? ' aria-current="page"' : '') . '>' . authH($s[1]) . '</a>', $subs[$label]));
        $nav .= '<div class="nav-group' . ($here ? ' current' : '') . '">' . $top . '<button class="nav-sub-toggle" type="button" aria-expanded="false" aria-controls="' . $id . '"><span class="visually-hidden">'
            . authH($label) . ' pages</span></button><div class="nav-sub" id="' . $id . '">' . $items . '</div></div>';
    }
    return '<header class="site-header"><a class="brand" href="/" aria-label="Monzero home"><img class="brand-mark brand-coin" src="/assets/monzero-coin-transparent-20261018-96.webp" alt="" width="32" height="32"><span>MONZERO</span></a>'
        . '<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button><nav id="site-nav" aria-label="Primary navigation">' . $nav . '</nav>'
        . '<a class="header-cta" href="/#download">Download <span aria-hidden="true">↗</span></a></header>';
}
