/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

// The visible texts come from the template (editable website texts quote.files.selected
// and quote.form.submitting), rendered as data attributes on .wasm-quote-form-container.
publicWidget.registry.WasmQuoteWidget = publicWidget.Widget.extend({
    selector: '.wasm-quote-form-container',
    events: {
        'change input[type="file"]': '_onFileChange',
        'submit form': '_onSubmitForm',
    },

    _onFileChange: function (ev) {
        const input = ev.currentTarget;
        const fileList = input.files;
        const infoBox = this.$('.wasm-file-list-info');

        if (infoBox.length && fileList.length > 0) {
            const alertBox = document.createElement('div');
            alertBox.className = 'alert alert-info mt-2 mb-0';
            const header = document.createElement('strong');
            header.className = 'd-block mb-1';
            header.textContent = (this.el.dataset.filesLabel || '').replace('{n}', fileList.length);
            alertBox.appendChild(header);
            for (let i = 0; i < fileList.length; i++) {
                const sizeMB = (fileList[i].size / 1024 / 1024).toFixed(2);
                if (i > 0) {
                    alertBox.appendChild(document.createElement('br'));
                }
                const icon = document.createElement('i');
                icon.className = 'fa fa-file-pdf-o me-1 text-danger';
                alertBox.appendChild(icon);
                alertBox.appendChild(document.createTextNode(' ' + fileList[i].name + ' (' + sizeMB + ' MB)'));
            }
            infoBox.empty().append(alertBox);
        }
    },

    _onSubmitForm: function (ev) {
        const btn = this.$('button[type="submit"]');
        if (btn.length) {
            const icon = document.createElement('i');
            icon.className = 'fa fa-circle-o-notch fa-spin me-2';
            btn.prop('disabled', true).empty().append(
                icon,
                document.createTextNode(' ' + (this.el.dataset.submittingLabel || ''))
            );
        }
    },
});
