import smbus
import MySQLdb
import time
import logging
import numpy as np

# Device ID
CCS811_ADDRESS = 0x5B

# Register Address for CCS811
STATUS = 0x00
MEAS_MODE = 0x01
ALG_RESULT_DATA = 0x02
ERROR_ID = 0xE0
HW_ID = 0x20
APP_START = 0xF4
ENV_DATA = 0x05
SW_RESET = 0XFF

def error_handling(err_message):
    logging.basicConfig(filename='CCS811_BME280_RPi_Error.log', encoding='utf-8', level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
    logging.error(err_message)

def warning_handling(warning_message):
    logging.basicConfig(filename='CCS811_BME280_RPi_Error.log', encoding='utf-8', level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
    logging.warning(warning_message)

def read_CCS811():
    i2c = smbus.SMBus(1)

    # i2c.write_byte_data(addr, 0x06, 0xF0)

    # CCS811 Connection Check
    try:
        buf_rx = i2c.read_byte_data(CCS811_ADDRESS, HW_ID)
    except:
        error_handling('I2C communication error')
        exit()

    if buf_rx == 0x81:
        print('Device ID is', hex(buf_rx))
        print('CCS811 is connected.')
    else:
        # Warning Handling
        print('CCS811 connection is failed.')
        warning_handling('CCS811 connection is failed.')
        # SW reset on CCS811
        try:
            i2c.write_i2c_block_data(CCS811_ADDRESS, SW_RESET, [0x11, 0xE5, 0x72, 0x8A])
        except:
            error_handling('I2C communication error')
            exit()

        time.sleep(5)
        try:
            buf_rx = i2c.read_byte_data(CCS811_ADDRESS, HW_ID)
        except:
            error_handling('I2C communication error')
            exit()

        if buf_rx != 0x81:
            print('CCS811 connection is failed after SW reset.')
            error_handling('CCS811 connection is failed after SW reset.')
            exit()

    # CCS811 Status Check
    try:
        buf_rx = i2c.read_byte_data(CCS811_ADDRESS, STATUS)
    except:
        error_handling('I2C communication error')
        exit()

    CCS811_Status = buf_rx
    if (CCS811_Status & 0b00010000) >> 4 != 0x01:
        # Error Handling
        print('No application firmware loaded for CCS811')
        error_handling('No application firmware loaded for CCS811')
        exit()

    if (CCS811_Status & 0x01) == 0x01:
        # Error Handling
        print('CCS811 is in Error')
        try:
            buf_rx = i2c.read_byte_data(CCS811_ADDRESS, ERROR_ID)
        except:
            error_handling('I2C communication error')
            exit()
        print(hex(buf_rx))
        error_handling('Exit with error code %s' % hex(buf_rx))
        exit()

    # CCS811 Status Check
    try:
        buf_rx = i2c.read_byte_data(CCS811_ADDRESS, STATUS)
    except:
        error_handling('I2C communication error')
        exit()
    CCS811_Status = buf_rx

    if (CCS811_Status & 0b10000000) >> 7 != 0x01:
        print('Start Application mode')
        # Start Application of CCS811
        try:
            i2c.write_byte(CCS811_ADDRESS, APP_START)
        except:
            error_handling('I2C communication error')
            exit()
        # CCS811 Status Check again
        try:
            buf_rx = i2c.read_byte_data(CCS811_ADDRESS, STATUS)
        except:
            error_handling('I2C communication error')
            exit()
        CCS811_Status = buf_rx

        if (CCS811_Status & 0b10000000) >> 7 != 0x01:
            # Error Handling
            print('Start Application mode cannot be started for CCS811.')
            error_handling('Start Application mode cannot be started for CCS811.')
            exit()
    else:
        print('Application mode is in active.')

    # CCS811 Measurement Mode setting
    try:
        buf_rx = i2c.read_byte_data(CCS811_ADDRESS, MEAS_MODE)
    except:
        error_handling('I2C communication error')
        exit()
    DriveMode = buf_rx & 0b01110000 >> 4
    if DriveMode != 0x01:
        buf_tx = (buf_rx & ~0b11110000) | (0b00010000)
        try:
            i2c.write_byte_data(CCS811_ADDRESS, MEAS_MODE, buf_tx)
        except:
            error_handling('I2C communication error')
            exit()
        print('Measure Mode is set to Mode1.')
        time.sleep(5)
    else:
        print('Measure Mode is in Mode1.')

    # Receive Data
    try:
        buf_rx = i2c.read_i2c_block_data(CCS811_ADDRESS, ALG_RESULT_DATA, 8)
    except:
        error_handling('I2C communication error')
        exit()
    print(buf_rx)
    eCO2 = buf_rx[0]*256+buf_rx[1]
    eTVOC = buf_rx[2]*256+buf_rx[3]
    print('eCO2:', eCO2)
    print('eTVOC:', eTVOC)

    return eCO2, eTVOC

def read_BME280():
    i2c = smbus.SMBus(1)
    # Device ID
    BME280_ADDRESS = 0x77
    # Register Address for BME280
    BME280_ID = 0xD0
    BME280_CTRL_MEAS = 0xF4
    BME280_TEMP = 0xFA
    BME280_PRESS = 0xF7
    # BME280 Connection Check
    try:
        buf_rx = i2c.read_byte_data(BME280_ADDRESS, BME280_ID)
    except:
        print('I2C communication error')
        error_handling('I2C communication error')
        exit()

    if buf_rx == 0x60:
        print('Device ID is', hex(buf_rx))
        print('BME280 is connected.')
    else:
        # Warning Handling
        print('BME280 connection is failed.')
        error_handling('BME280 connection is failed.')
        exit()

    # Measurement mode configuration
    buf_tx = 0b10110101
    try:
        buf_rx = i2c.write_byte_data(BME280_ADDRESS, BME280_CTRL_MEAS, buf_tx)
    except:
        print('I2C communication error')
        error_handling('I2C communication error')
        exit()

    # Measure Temperature
    try:
        buf_rx = i2c.read_i2c_block_data(BME280_ADDRESS, BME280_TEMP, 3)
    except:
        error_handling('I2C communication error')
        exit()

    Temp_hex = (buf_rx[0] << 12) | ((buf_rx[1] << 4)) | (buf_rx[2] >> 4)

    try:
        buf_rx = i2c.read_i2c_block_data(BME280_ADDRESS, 0x88, 6)
    except:
        error_handling('I2C communication error')
        exit()

    dig_T1 = buf_rx[0] | buf_rx[1] << 8
    dig_T2 = buf_rx[2] | buf_rx[3] << 8
    dig_T3 = buf_rx[4] | buf_rx[5] << 8

    dig_T1 = np.uint16(dig_T1)
    dig_T2 = np.uint16(dig_T2)
    dig_T2 = dig_T2.astype('int16')
    dig_T3 = np.uint16(dig_T3)
    dig_T3 = dig_T3.astype('int16')

    var1 = np.int32((((Temp_hex >> 3) - (dig_T1.astype('int32') << 1)) * dig_T2.astype('int32')) >> 11)
    var2 = np.int32((((((Temp_hex >> 4) - dig_T1.astype('int32')) * ((Temp_hex >> 4) - dig_T1.astype('int32'))) >> 12) *  dig_T3.astype('int32')) >> 14)

    t_fine = var1 + var2
    Temp = (t_fine * 5 + 128) >> 8
    Temp = Temp * 0.01
    print('Temperature %.2f degC' % Temp)

    # Measure Pressure
    try:
        buf_rx = i2c.read_i2c_block_data(BME280_ADDRESS, BME280_PRESS, 3)
    except:
        error_handling('I2C communication error')
        exit()

    Press_hex = (buf_rx[0] << 12) | ((buf_rx[1] << 4)) | (buf_rx[2] >> 4)

    try:
        buf_rx = i2c.read_i2c_block_data(BME280_ADDRESS, 0x8E, 18)
    except:
        error_handling('I2C communication error')
        exit()

    dig_P1 = buf_rx[0] | buf_rx[1] << 8
    dig_P2 = buf_rx[2] | buf_rx[3] << 8
    dig_P3 = buf_rx[4] | buf_rx[5] << 8
    dig_P4 = buf_rx[6] | buf_rx[7] << 8
    dig_P5 = buf_rx[8] | buf_rx[9] << 8
    dig_P6 = buf_rx[10] | buf_rx[11] << 8
    dig_P7 = buf_rx[12] | buf_rx[13] << 8
    dig_P8 = buf_rx[14] | buf_rx[15] << 8
    dig_P9 = buf_rx[16] | buf_rx[17] << 8

    dig_P1 = np.uint16(dig_P1)
    dig_P2 = np.uint16(dig_P2)
    dig_P2 = dig_P2.astype('int16')
    dig_P3 = np.uint16(dig_P3)
    dig_P3 = dig_P3.astype('int16')
    dig_P4 = np.uint16(dig_P4)
    dig_P4 = dig_P4.astype('int16')
    dig_P5 = np.uint16(dig_P5)
    dig_P5 = dig_P5.astype('int16')
    dig_P6 = np.uint16(dig_P6)
    dig_P6 = dig_P6.astype('int16')
    dig_P7 = np.uint16(dig_P7)
    dig_P7 = dig_P7.astype('int16')
    dig_P8 = np.uint16(dig_P8)
    dig_P8 = dig_P8.astype('int16')
    dig_P9 = np.uint16(dig_P9)
    dig_P9 = dig_P9.astype('int16')

    var1 = np.int64(t_fine - 128000)
    var2 = np.int64(var1 * var1 * dig_P6.astype('int64'))
    var2 = var2 + ((var1 * dig_P5.astype('int64')) << 17)
    var2 = var2 + (dig_P4.astype('int64') << 35)
    var1 = ((var1 * var1 * dig_P3.astype('int64')) >> 8) + ((var1 * dig_P2.astype('int64')) << 12)
    var1 = ((1 << 47) + var1) * dig_P1.astype('int64') >> 33

    p = np.int64(1048576 - Press_hex)
    p = (((p << 31) - var2) * 3125) / var1
    p = p.astype('int64')

    var1 = (dig_P9.astype('int64') * (p >> 13) * (p >> 13)) >> 25
    var2 = (dig_P8.astype('int64') * p) >> 19
    p = ((p + var1 + var2) >> 8) + (dig_P7.astype('int64') << 4)

    Press = p / 256 * 0.01
    print('Pressure %.2f hPa' % Press)

    return Press


if __name__ == '__main__':
    # Read CCS811 Value
    eCO2, eTVOC = read_CCS811()
    Pressure = read_BME280()
    # Connect to SQL server
    connector = MySQLdb.connect(host='133.18.232.25', db='roomconditionmonitor', user='user_roomcondition', passwd='pass_roomcondition', charset='utf8')
    cursor = connector.cursor()

    sql = "insert into roomcondition_table(id,date,eCO2,eTVOC, atom_pressure) values(0,now(),'%d', '%d', '%.3f');" %(eCO2, eTVOC, Pressure)
    cursor.execute(sql)
    connector.commit()

    cursor.close()
    connector.close()
