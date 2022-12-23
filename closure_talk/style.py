_STYLE = """
.char-list-item:after {
    border-bottom: 1px dashed #bbb;
    bottom: 0;
    content: "";
    left: 20px;
    position: absolute;
    right: 20px
}

.top-bar .MuiOutlinedInput-root svg {
    color: inherit
}

.top-bar .MuiOutlinedInput-root fieldset, .top-bar .MuiOutlinedInput-root:hover fieldset {
    border-color: inherit !important
}

.stamp-btn {
    height: 60px;
    width: 60px
}

.akn-item {
    align-items: flex-start;
    -webkit-column-gap: 12px;
    column-gap: 12px;
    display: flex;
    margin-left: 12px;
    padding-bottom: 12px;
    padding-right: 12px
}

.akn-avatar {
    flex-shrink: 0;
    height: 60px;
    width: 60px
}

.akn-avatar img {
    background-image: linear-gradient(#0c0c0c, #3c3c3c);
    height: 100%;
    object-fit: cover;
    width: 100%
}

.akn-content {
    background-color: #0e0e0e;
    border: 1px solid #484848;
    color: #ddd;
    flex-grow: 1;
    padding: 8px;
    width: 100%
}

.akn-content.akn-content-thoughts {
    background-color: #3c3c3c;
    border: none;
    color: #999
}

.akn-content img {
    max-width: 100%
}

.akn-content img.akn-stamp {
    max-width: 40%
}

.akn-content-text {
    line-break: loose;
    overflow-wrap: break-word;
    white-space: pre-wrap
}

.akn-header {
    align-items: center;
    display: flex;
    flex-direction: row;
    padding-bottom: 20px
}

.akn-header-left {
    background-color: #a2a2a2;
    color: #323232;
    font-family: monospace;
    font-size: 12px;
    font-weight: 600;
    height: 14px;
    margin: 3px 0 3px 1px;
    text-align: center;
    width: 72px
}

.akn-header-title {
    -webkit-font-feature-settings: "zero";
    font-feature-settings: "zero";
    color: #d4d4d4;
    font-family: Optima, sans-serif;
    font-size: 16px;
    font-variant-numeric: slashed-zero;
    margin-left: -1px;
    padding: 0 8px;
    position: relative
}

.akn-header-title-deco {
    background-color: #a2a2a2;
    height: 2px;
    position: absolute;
    width: 2px
}

.akn-header-title-deco-1 {
    left: 0;
    top: 0
}

.akn-header-title-deco-2 {
    right: 0;
    top: 0
}

.akn-header-title-deco-3 {
    bottom: 0;
    left: 0
}

.akn-header-title-deco-4 {
    bottom: 0;
    right: 0
}

.akn-header-right {
    background-color: #484848;
    flex-grow: 1;
    height: 1px
}

.akn-insert-indicator {
    border-top: 1px dashed #a2a2a2;
    height: 2px;
    margin: 20px 80px
}

.akn-choices {
    align-items: flex-end;
    display: flex;
    flex-direction: column;
    gap: 24px;
    margin-bottom: 40px;
    padding-right: 12px
}

.akn-choice {
    background-color: #666;
    color: #eee;
    display: flex;
    justify-content: space-between;
    min-width: 300px;
    padding: 8px;
    text-align: right
}

.akn-choice .icon {
    padding-top: 2px
}

.akn-selection {
    height: 72px;
    margin: 24px 12px 0
}

.akn-selection .akn-selection-content {
    background-color: #565051;
    border: 1px solid #888;
    color: #eee;
    display: flex;
    justify-content: space-between;
    padding: 8px
}

.akn-selection .icon {
    padding-top: 2px
}

.akn-narration {
    color: #eee;
    margin-bottom: 12px;
    margin-left: 92px;
    margin-right: 24px;
    min-height: 60px
}

.yuzu-item {
    grid-column-gap: 16px;
    -webkit-column-gap: 16px;
    column-gap: 16px;
    display: grid;
    grid-template-columns:64px minmax(0, 1fr);
    grid-template-rows:1fr;
    padding: 8px 24px 0 16px
}

.yuzu-left {
    grid-column: 1
}

.yuzu-right {
    display: flex;
    flex-direction: column;
    grid-column: 2;
    justify-content: space-between
}

.yuzu-message-box {
    background-color: #4c5b70;
    border-radius: 10px;
    color: #fff;
    font-size: 20px;
    line-height: 24px;
    max-width: 100%;
    padding: 8px;
    position: relative;
    width: -webkit-fit-content;
    width: -moz-fit-content;
    width: fit-content
}

.yuzu-image-box {
    background-color: #fff;
    border: 1px solid #e7ebec;
    border-radius: 10px;
    max-width: 75%;
    padding: 8px
}

.yuzu-image-box.yuzu-stamp {
    width: 40%
}

.yuzu-message {
    font-weight: 400;
    line-break: loose;
    overflow-wrap: break-word;
    position: relative;
    white-space: pre-wrap
}

.yuzu-message img {
    max-width: 100%
}

.yuzu-name {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 4px
}

.yuzu-avatar-box {
    height: 64px;
    width: 64px
}

.yuzu-avatar-box img {
    background-color: rgba(0, 0, 0, .04);
    border-radius: 50%;
    height: 100%;
    object-fit: cover;
    width: 100%
}

.yuzu-item.yuzu-player-item {
    -webkit-column-gap: 24px;
    column-gap: 24px;
    justify-items: flex-end;
    padding: 16px 16px 0
}

.yuzu-player-box {
    grid-column: 2
}

.yuzu-message-box.yuzu-player-box {
    background-color: #4a8aca
}

.yuzu-message-box.yuzu-avatar-message-box:before {
    border-color: transparent #4c5b70 transparent transparent;
    border-style: solid;
    border-width: 5px 5px 5px 0;
    content: "";
    display: block;
    height: 0;
    left: -5px;
    position: absolute;
    top: 10px;
    width: 0
}

.yuzu-message-box.yuzu-player-box:before {
    border-color: transparent transparent transparent #4a8aca;
    border-style: solid;
    border-width: 5px 0 5px 5px;
    content: "";
    display: block;
    height: 0;
    position: absolute;
    right: -5px;
    top: 10px;
    width: 0
}

.yuzu-insert-indicator {
    border-top: 1px dashed #a2a2a2;
    height: 2px;
    margin: 10px 80px 0
}

.yuzu-item.yuzu-special-item {
    padding: 16px 24px 0 16px
}

.yuzu-kizuna-item {
    background-color: transparent;
    border: 1px solid #d8d8d8;
    border-radius: 10px;
    grid-column: 2;
    overflow: hidden;
    padding: 16px;
    position: relative;
    z-index: 1
}

.yuzu-kizuna-header {
    border-bottom: 1px solid #d8d8d8;
    padding-bottom: 8px
}

.yuzu-kizuna-header .text {
    border-left: 2px solid #ff92a4;
    color: #4c5b70;
    font-size: 18px;
    font-weight: 700;
    padding: 0 8px
}

.yuzu-kizuna-heart {
    background-color: #ffedf1;
    height: 110%;
    left: -5%;
    position: absolute;
    text-align: right;
    top: -5%;
    width: 110%;
    z-index: -1
}

.yuzu-kizuna-footer {
    margin-top: 8px
}

.yuzu-kizuna-footer .text {
    background-color: #ff92a4;
    border: 1px solid #ff92a4;
    border-radius: 5px;
    color: #fff;
    display: block;
    font-size: 16px;
    font-weight: 700;
    padding: 8px 0;
    position: relative;
    text-align: center;
    width: 100%
}

.yuzu-kizuna-footer .text:after, .yuzu-reply-choices .text:after {
    background-color: rgba(0, 0, 0, .5);
    border-radius: 5px;
    content: "";
    display: block;
    -webkit-filter: blur(2px);
    filter: blur(2px);
    height: calc(100% + 4px);
    left: 0;
    position: absolute;
    top: 0;
    width: 100%;
    z-index: -1
}

.yuzu-reply-item {
    background-color: #f3f7f8;
    border: 1px solid #d8d8d8;
    border-radius: 10px;
    grid-column: 2;
    overflow: hidden;
    padding: 16px;
    position: relative;
    z-index: 1
}

.yuzu-reply-header {
    border-bottom: 1px solid #d8d8d8;
    padding-bottom: 8px
}

.yuzu-reply-header .text {
    border-left: 2px solid #3493f9;
    color: #4c5b70;
    font-size: 18px;
    font-weight: 700;
    padding: 0 8px
}

.yuzu-reply-choices {
    margin-top: 8px
}

.yuzu-reply-choice:not(:last-of-type) {
    margin-bottom: 8px
}

.yuzu-reply-choice {
    background-color: #fff;
    border: 1px solid #e7ebec;
    border-radius: 5px;
    color: #4c5b70;
    font-size: 18px;
    font-weight: 700;
    line-height: 24px;
    min-height: 24px;
    overflow-wrap: break-word;
    padding: 8px;
    position: relative;
    text-align: center;
    white-space: pre-wrap
}

.yuzu-narration-item {
    grid-column: 1/span 2;
    padding: 12px;
    text-align: center
}

.yuzu-narration-item .text {
    color: #4c5b70;
    font-size: 18px;
    font-weight: 700;
    white-space: pre-wrap
}

body {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen, Ubuntu, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;
    margin: 0
}

code {
    font-family: source-code-pro, Menlo, Monaco, Consolas, Courier New, monospace
}

.MuiDialogContent-root {
    display: flex;
    flex-direction: column;
    gap: 12px
}
"""