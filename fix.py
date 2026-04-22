f = open('bot/orders.py', 'r', encoding='utf-8')
c = f.read()
f.close()

old = "    print(f\"  \U0001f389  Order submitted successfully! (orderId: {response.get('orderId')})\\n\")"
new = "    order_id = response.get('orderId') or response.get('algoId', 'N/A')\n    print(f\"  \U0001f389  Order submitted successfully! (orderId: {order_id})\\n\")"

if old in c:
    f = open('bot/orders.py', 'w', encoding='utf-8')
    f.write(c.replace(old, new))
    f.close()
    print("Fixed!")
else:
    print("Not found - trying alt...")
    old2 = "submitted successfully! (orderId: {response.get('orderId')})"
    new2 = "submitted successfully! (orderId: {response.get('orderId') or response.get('algoId', 'N/A')})"
    if old2 in c:
        f = open('bot/orders.py', 'w', encoding='utf-8')
        f.write(c.replace(old2, new2))
        f.close()
        print("Fixed with alt!")
    else:
        print("Still not found")