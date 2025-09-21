/** @odoo-module */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onWillStart } from "@odoo/owl";

patch(OrderReceipt.prototype, {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.state = useState({ qr_code: false });

        this.getTaxManQRCode = async () => {
            const pos_orders = await this.orm.call(
                "pos.order",
                "search_read",
                [[["pos_reference", "=", this.props.data.name]], ["x_taxman_qr_code"]]
            );

            if (pos_orders.length && pos_orders[0].x_taxman_qr_code) {
                this.state.qr_code = pos_orders[0].x_taxman_qr_code;
                return true; // QR code found
            }
            return false; // QR code not ready yet
        };

        this.pollQRCode = async (maxRetries = 30, interval = 2000) => {
            let attempts = 0;
            const tryFetch = async () => {
                const found = await this.getTaxManQRCode();
                attempts++;
                if (!found && attempts < maxRetries) {
                    setTimeout(tryFetch, interval);
                }
            };
            tryFetch();
        };

        onMounted(() => {
            this.pollQRCode(); // start polling on mount
        });
    },
});
