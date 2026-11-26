# Parts stock-out
Use when: a category cycle time jumps and parts_availability shows in_stock false or a long lead time.
Actions: 1) Confirm the stock-out in parts_availability for the affected site and weeks. 2) Transfer stock from the nearest healthy site (check lead time versus inter-site transfer). 3) Raise the reorder point and safety stock for that part, sized to lead time times weekly use. 4) Cannibalise only from vehicles already waiting for parts. 5) Notify dispatch so affected vehicles are routed to sites with stock.
Owner: Parts and logistics. Review: every 48 hours during the shortage.
