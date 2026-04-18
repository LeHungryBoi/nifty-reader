// ==UserScript==
// @name         Nifty.org - Semantic Story Cleaner
// @namespace    https://github.com/LeHungryBoi/nifty-clean-up-js
// @version      3.8
// @description  Adds semantic paragraphs, indent, and compact line-height for better readability.
// @author       LeHungryBoi
// @match        https://www.nifty.org/nifty/*
// @match        https://nifty.org/nifty/*
// @grant        none
// @run-at       document-end
// @updateURL    https://raw.githubusercontent.com/LeHungryBoi/nifty-clean-up-js/main/nifty-clean-up.js
// @downloadURL  https://raw.githubusercontent.com/LeHungryBoi/nifty-clean-up-js/main/nifty-clean-up.js
// ==/UserScript==

(function () {
    'use strict';

    function isStoryPage() {
        const hasPre = !!document.querySelector('pre');
        const hasTableStuff = document.querySelectorAll('tr, td').length > 0;
        return hasPre && !hasTableStuff;
    }

    if (isStoryPage()) {
        console.log('✅ Story page detected — fixing text');
        const pre = document.querySelector('pre');
        if (!pre) return;

        let text = pre.textContent;
        text = text.replace(/(\S)\n(\S)/g, '$1 $2');
        text = text.replace(/ +/g, ' ');

        const paragraphBlocks = text.split(/\n{2,}/);
        const article = document.createElement('article');
        article.id = 'story-content';

        paragraphBlocks.forEach(block => {
            const trimmed = block.trim();
            if (trimmed.length > 0) {
                const p = document.createElement('p');
                p.textContent = trimmed;
                article.appendChild(p);
            }
        });

        pre.parentNode.replaceChild(article, pre);
        console.log(`✅ Text refactored: ${paragraphBlocks.length} paragraphs generated.`);
    }

    const style = document.createElement('style');
    style.textContent = `
        html, body {
            margin: 0 !important;
            width: 100% !important;
            max-width: none !important;
            box-sizing: border-box !important;
            font-size: 1rem !important; 
            /* 移动端紧凑行高 */
            line-height: 1.45 !important;
            font-family: Georgia, serif !important;
            padding: 8px 2px !important; 
            -webkit-text-size-adjust: 100%;
        }

        article#story-content {
            width: 100%;
            max-width: 850px;
            margin: 0 auto;
        }

        p {
            /* 配合紧凑行高，稍微缩小段间距 */
            margin-bottom: 0.8em !important;
            display: block !important;
            text-indent: 2em !important;
        }

        @media (min-width: 768px) {
            html, body {
                font-size: 1.1rem !important;
                /* 桌面端稍微放松一点点，但依然保持紧凑 */
                line-height: 1.6 !important;
                padding: 20px 40px !important;
            }
            p {
                margin-bottom: 1em !important;
                text-indent: 2.5em !important;
            }
        }

        @media (prefers-color-scheme: dark) {
            html, body {
                background-color: #121212 !important;
                color: #e0e0e0 !important;
            }
        }
    `;
    document.head.appendChild(style);
    console.log('✅ Nifty script v3.8 (Compact Line-height) loaded');
})();
