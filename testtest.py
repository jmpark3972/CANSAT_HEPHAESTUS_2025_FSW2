import board, busio, time
i2c = busio.I2C(board.SCL, board.SDA)
while not i2c.try_lock(): pass
print("I2C scan:", [hex(a) for a in i2c.scan()])
i2c.unlock()
