import json


class Assembler:
    def __init__(self, size_bytes = 64, value_size_bytes = 4, logging = True):
        self.data = 0
        self.size_bytes = size_bytes
        
        if value_size_bytes < 1 or value_size_bytes > size_bytes:
            value_size_bytes = 1
        self.value_size_bytes = value_size_bytes
        
        self.max_address = (size_bytes - self.value_size_bytes)*8
        self.max_value = 2**(self.value_size_bytes*8) - 1
        self.maska_data = 2**(self.size_bytes*8) - 1

        self.logging = logging
        self.operation_num = 1

        if logging:
            print(f"Размер памяти: {size_bytes} байт. Размер значения: {value_size_bytes}")
            print(f"Количество уникальных адресов: {self.max_address}. Диапазон адресов: [0, {self.max_address}]")
            print(f"Количество уникальных значений: {self.max_value}. Диапазон значений: [0, {self.max_value}]")

    def _check_address(self, address):
        if address < 0 or address > self.max_address:
            raise ValueError(f"Адрес {address} вне диапазона [0, {self.max_address}]")
        
    def _check_value(self, value):
        if value < 0 or value > self.max_value:
            raise ValueError(f"Число {value} вне диапазона [0, {self.max_value}]")
        
    def _print(self, message):
        print(f"Номер операции {self.operation_num}: " + message)
   

    def execute(self, bin_code):
        comms = self._split_bin_code(bin_code)
        for i, record in enumerate(comms, 1):
            com = self.unpack_value_from_bytes(record)
            
            if self.logging:
                print(com, end=' ')

            match com[0]:
                case 0: # LOAD_CON
                    self.__command_LOAD_CON(com[1], com[2])
                case 12: # READ
                    self.__command_READ(com[1], com[2])
                case 13: # WRITE
                    self.__command_WRITE(com[1], com[2])
                case 27: # POW
                    self.__command_POW(com[1], com[2])
            
            self.operation_num+=1

    # Загрузка константы
    def __command_LOAD_CON(self, val1, val2):
        self._check_address(val1)
        self._check_value(val2)

        clear_mask = ~(self.max_value << val1)

        data = self.data
        data = data & clear_mask
        val2_to_write = (self.max_value & val2) << val1
        self.data = data | val2_to_write

        if self.logging:
            self._print(f"Запись по адресу {val1} значения {val2}")

    # Чтение из памяти
    def __command_READ(self, val1, val2):
        self._check_address(val1)
        readed_val = self.max_value & (self.data >> val1)
        
        if self.logging:
            self._print(f"Чтение из адреса {val1} значения {readed_val}")
        else:
            self._print(readed_val)

    # Запись в память
    def __command_WRITE(self, val1, val2):
        self._check_address(val1)
        self._check_address(val2)

        readed_val = self.max_value & (self.data >> val1)
        clear_mask = ~(self.max_value << val2)

        data = self.data
        data = data & clear_mask
        value_to_write = (self.max_value & readed_val) << val2
        self.data = data | value_to_write

        if self.logging:
            self._print(f"Запись из адреса {val1} значения {readed_val} в адрес {val2}")
        
    # Возведение в степень
    def __command_POW(self, val1, val2):
        self._check_address(val1)
        self._check_address(val2)

        readed_val1 = self.max_value & (self.data >> val1)
        readed_val2 = self.max_value & (self.data >> val2)
        val_pow = (readed_val1**readed_val2)%self.max_value

        data = self.data
        clear_mask = ~(self.max_value << val1)
        data = data & clear_mask
        value_to_write = (self.max_value & val_pow) << val1
        self.data = data | value_to_write

        if self.logging:
            self._print(f"Запись в адрес {val1} значения {val_pow}, которое является возведения числа {readed_val1} по адресу {val1} в степень {readed_val2} по адресу {val2}")


    def _split_bin_code(self, bin_code):
        comms = []
        record_size = 6
        records = [bin_code[i:i+record_size] for i in range(0, len(bin_code), record_size)]
        for i, record in enumerate(records, 1):
            comms.append(record)
        return comms
    
    def test_read_bin_code(self, bin_code):
        comms = self._split_bin_code(bin_code)
        for i, record in enumerate(comms, 1):
            print(f"Запись {i}: {record.hex()} : {self.unpack_value_from_bytes(record)}")
        
    
    def pack_values(self, var1, var2, var3):
        # Проверка на переполнение
        max_val1 = (1 << 5) - 1
        max_val2 = (1 << 24) - 1
        max_val3 = (1 << 12) - 1
        
        if var1 > max_val1:
            raise ValueError(f"Значение var1={var1} превышает максимальное {max_val1} для {5} бит")
        if var2 > max_val2:
            raise ValueError(f"Значение var2={var2} превышает максимальное {max_val2} для {24} бит")
        if var3 > max_val3:
            raise ValueError(f"Значение var3={var3} превышает максимальное {max_val3} для {12} бит")

        result = (var1 << 36) | (var2 << 12) | var3
        
        return result

    def _get_assemble_bytes(self, command, val1 = 0, val2 = 0):
        command_code = 0
        match command:
            case "LOAD_CON":
                command_code = 0
            case "READ":
                command_code = 12
            case "WRITE":
                command_code = 13
            case "POW":
                command_code = 27
        
        return self.pack_values(command_code, val1, val2).to_bytes(6, 'big')
    
    def unpack_value(self, value):
        # Извлекаем var3 (биты 28-39) - 12 бит
        var3 = value & ((1 << 12) - 1)
        
        # Извлекаем var2 (биты 5-27) - 23 бита
        var2 = (value >> 12) & ((1 << 24) - 1)
        
        # Извлекаем var1 (биты 0-4) - 5 бит
        var1 = (value >> 36) & ((1 << 5) - 1)
        
        return var1, var2, var3

    def unpack_value_from_bytes(self, value):
        return self.unpack_value(int.from_bytes(value, byteorder='big'))
    

class FileManager:
    def __init__(self):
        pass

    def read(self, file_name: str):
        with open(file_name, 'r') as file:
            data = json.load(file)
            return data['program']
        return None
    
    def write_bin(self, file_name: str, text):
        with open(file_name, 'wb') as file:
            file.write(text)

    def read_bin(self, file_name: str):
        with open(file_name, 'rb') as file:
            return file.read()


FILE_INPUT = "input.json"
FILE_OUTPUT = "output.txt"
TEST_MODE = "TEST"

file_manager = FileManager()

arr = file_manager.read(FILE_INPUT)
res = int(0).to_bytes(0, 'big')
assembler = Assembler()

for val in arr:
    temp = assembler._get_assemble_bytes(*val)
    res += temp

file_manager.write_bin(FILE_OUTPUT, res)
res_bin = file_manager.read_bin(FILE_OUTPUT)
assembler.execute(res_bin)

print(f"Память: {assembler.data}")
print(f"Память (бинарное представление): {bin(assembler.data)}")