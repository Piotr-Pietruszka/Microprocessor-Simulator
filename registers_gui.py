import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from myUi import *
import re
import time
import datetime
from sys import exit
import threading
from file_browser import FileBrowser
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog

class Register:
    def __init__(self, name):
        self.name = name
        self.high_byte = bytes(1)
        self.low_byte = bytes(1)

    def move_into(self, wartosc, czesc, is_int=False):
        if is_int:
            wartosc = wartosc.to_bytes(1, byteorder='big')

        if czesc:
            # czesc starsza
            self.high_byte = wartosc
        else:
            # czesc mlodsza
            self.low_byte = wartosc

    def add(self, wartosc, czesc, is_int=True):
        """
         Domyslnie wartosc to int, jesli nie to uznaje ze to byte
        """
        if not is_int:
            wartosc = int.from_bytes(wartosc, byteorder='big')
        if czesc:
            # czesc starsza
            reg_this = int.from_bytes(self.high_byte, byteorder='big')
        else:
            # czesc mlodsza
            reg_this = int.from_bytes(self.low_byte, byteorder='big')

        reg_this += wartosc
        if reg_this > 255:
            reg_this = reg_this % 255

        if czesc:
            # czesc starsza
            self.high_byte = reg_this.to_bytes(1, byteorder='big')
        else:
            # czesc mlodsza
            self.low_byte = reg_this.to_bytes(1, byteorder='big')

    def sub(self, wartosc, czesc, is_int=True):
        """
        Domyslnie wartosc to int, jesli nie to uznaje ze to byte
        """
        if not is_int:
            wartosc = int.from_bytes(wartosc, byteorder='big')

        if czesc:
            # czesc starsza
            reg_this = int.from_bytes(self.high_byte, byteorder='big')
        else:
            # czesc mlodsza
            reg_this = int.from_bytes(self.low_byte, byteorder='big')

        reg_this -= wartosc
        if reg_this < 0:
            # Przypadek gdy wartosc jest mniejsza od 0
            reg_this = abs(reg_this)
        if czesc:
            # czesc starsza
            self.high_byte = reg_this.to_bytes(1, byteorder='big')
        else:
            # czesc mlodsza
            self.low_byte = reg_this.to_bytes(1, byteorder='big')

    def get_int(self, czesc):
        """
        Konwersja na int
        :param czesc: czesc starsza - 1, mlodsza - 0, obydiwe - -1
        :return: wartosc atrybutu high_byte/low_byte, w postaci inta
        """
        if czesc == -1:
            # obydwa bity
            bytes_2 = self.high_byte + self.low_byte
            return int.from_bytes(bytes_2, byteorder='big')
        elif czesc == 1:
            # czesc starsza
            return int.from_bytes(self.high_byte, byteorder='big')
        else:
            # czesc mlodsza
            return int.from_bytes(self.low_byte, byteorder='big')

    def get_byte(self, czesc):
        """
        :param czesc: starsza, mlodsza
        :return: wartosc atrybutu high_byte/low_byte, w postaci byte
        """
        if czesc:
            # czesc starsza
            return self.high_byte
        else:
            # czesc mlodsza
            return self.low_byte

    def set_bytes(self, bytes_2, is_int=False):
        """
        Zapisz czesc dolna i gorna
        :param bytes_2: 2 bajty
        :param is_int: czy wejscie w postaci int
        :return:
        """
        if is_int:
            bytes_2 = bytes_2.to_bytes(2, byteorder='big')
            self.high_byte = bytes_2[0].to_bytes(1, byteorder='big')
            self.low_byte = bytes_2[1].to_bytes(1, byteorder='big')
        else:
            self.high_byte = bytes_2[0].to_bytes(1, byteorder='big')  # to_bytes, bo po odczycie [0] - dostaje sie int
            self.low_byte = bytes_2[1].to_bytes(1, byteorder='big')


class Microprocesor_cal:

    def __init__(self, GUI):
        AX, BX, CX, DX = Register('AX'), Register('BX'), Register('CX'), Register('DX')
        self.registers = {'AX': AX, 'BX': BX, 'CX': CX, 'DX': DX}
        self.GUI = GUI
        # Slownik do dekodowania nazw
        self.registers_dec = {'AXL': ('AX', 0), 'AXH': ('AX', 1), 'BXL': ('BX', 0), 'BXH': ('BX', 1),
                              'CXL': ('CX', 0), 'CXH': ('CX', 1), 'DXL': ('DX', 0), 'DXH': ('DX', 1),
                              'AX': ('AX', -1), 'BX': ('BX', -1), 'CX': ('CX', -1), 'DX': ('DX', -1)}

        self.stack = []
        self.show_cursor = True

    def move_reg(self, reg_1, reg_2):
        """
        Przenosi rejestr 8-bitowy lun 16-bitowy
        :param reg_1: nazwa rejestru docelowego, z czescia np.AXL
        :param reg_2: nazwa rejestru z ktorego bierze sie dana lub wejscie w postaci stringa ('0'-'255)
        :return:
        """
        reg_1, czesc_1 = self.decode_reg(reg_1)

        # Caly rejestr 16-bitowy (do warunku wystarczy czesc_1, bo jesli  jest -1 (co oznzcza 16-bit,
        # to druga tez musi byc (te warunek sprawdzany wczesniej)
        if czesc_1 == -1:
            if reg_2 in self.registers_dec:
                reg_2, czesc_2 = self.decode_reg(reg_2)
                self.registers[reg_1].move_into(self.registers[reg_2].get_byte(1), 1)  # czesc starsza
                self.registers[reg_1].move_into(self.registers[reg_2].get_byte(0), 0)  # czesc mlodsza
            else:
                reg_2 = int(reg_2)
                byte_from_int_var = reg_2.to_bytes(2, byteorder='big')
                self.registers[reg_1].move_into(byte_from_int_var[0], 1, is_int=True)  # Czesc starsza
                self.registers[reg_1].move_into(byte_from_int_var[1], 0, is_int=True)  # Czesc mlodsza
            return

        # Rozkazy na czesciach (8-bit)
        if reg_2 in self.registers_dec:
            reg_2, czesc_2 = self.decode_reg(reg_2)
            self.registers[reg_1].move_into(self.registers[reg_2].get_byte(czesc_2), czesc_1)
        else:
            self.registers[reg_1].move_into(int(reg_2), czesc_1, is_int=True)

    def add_reg(self, reg_1, reg_2):

        reg_1, czesc_1 = self.decode_reg(reg_1)

        # Caly rejestr 16-bitowy
        if czesc_1 == -1:
            if reg_2 in self.registers_dec:
                reg_2, czesc_2 = self.decode_reg(reg_2)
                self.registers[reg_1].add(self.registers[reg_2].get_int(1), 1)  # czesc starsza
                self.registers[reg_1].add(self.registers[reg_2].get_int(0), 0)  # czesc mlodsza
            else:
                reg_2 = int(reg_2)
                byte_from_int_var = reg_2.to_bytes(2, byteorder='big')
                self.registers[reg_1].add(byte_from_int_var[0], 1)  # Czesc starsza
                self.registers[reg_1].add(byte_from_int_var[1], 0)  # Czesc mlodsza
            return

        if reg_2 in self.registers_dec:
            reg_2, czesc_2 = self.decode_reg(reg_2)
            self.registers[reg_1].add(self.registers[reg_2].get_int(czesc_2), czesc_1)
        else:
            self.registers[reg_1].add(int(reg_2), czesc_1)

    def sub_reg(self, reg_1, reg_2):
        reg_1, czesc_1 = self.decode_reg(reg_1)

        # Caly rejestr 16-bitowy
        if czesc_1 == -1:
            if reg_2 in self.registers_dec:
                reg_2, czesc_2 = self.decode_reg(reg_2)
                self.registers[reg_1].sub(self.registers[reg_2].get_int(1), 1)  # czesc starsza
                self.registers[reg_1].sub(self.registers[reg_2].get_int(0), 0)  # czesc mlodsza
            else:
                reg_2 = int(reg_2)
                byte_from_int_var = reg_2.to_bytes(2, byteorder='big')
                self.registers[reg_1].sub(byte_from_int_var[0], 1)  # Czesc starsza
                self.registers[reg_1].sub(byte_from_int_var[1], 0)  # Czesc mlodsza
            return

        if reg_2 in self.registers_dec:
            reg_2, czesc_2 = self.decode_reg(reg_2)
            self.registers[reg_1].sub(self.registers[reg_2].get_int(czesc_2), czesc_1)
        else:
            self.registers[reg_1].sub(int(reg_2), czesc_1)

    def show_register_int(self, reg):
        reg, czesc = self.decode_reg(reg)  # caly rejestr - jest zrobione w metodzie get_int
        return self.registers[reg].get_int(czesc)

    def show_register_byte(self, reg):
        reg, czesc = self.decode_reg(reg)
        return self.registers[reg].get_byte(czesc)

    def decode_reg(self, reg):
        reg_name, czesc, = self.registers_dec[reg]
        return reg_name, czesc

    def ex_instruction(self, line):
        """
        :param line: lista z rozdzielonymi: nazwa instrukcji  i argumentami
        Wykonanie podanej instrukcji na danych parametrach
        """
        if len(line) > 2:
            arg_2 = line[2]
        if len(line) > 1:
            arg_1 = line[1]

        instruction_name = line[0]
        if instruction_name == 'MOV':
            self.move_reg(arg_1, arg_2)
        elif instruction_name == 'ADD':
            self.add_reg(arg_1, arg_2)
        elif instruction_name == 'SUB':
            self.sub_reg(arg_1, arg_2)
        elif instruction_name == 'PUSH':
            self.push_stack(arg_1)
        elif instruction_name == 'POP':
            self.pop_stack(arg_1)
        elif instruction_name == 'INT21':
            self.interrupt_21H()
        elif instruction_name == 'INT33':
            self.interrupt_33H()

        else:
            print("Podano nieprawidlowa instrukcje")

    def pop_stack(self, reg):
        """
        Zdejmiij ze stosu ostatnia wartosc (16 bit) i zapisz do rejestru
        :param reg: rejestr do ktorego ma byc zapisana zmienna
        """
        reg, _ = self.decode_reg(reg)
        try:
            from_stack = self.stack.pop()
        except:
            # pusty stos - zwroc 0 (w 2 bajtach)
            empty_stack = 0
            empty_stack = empty_stack.to_bytes(2, byteorder='big')
            from_stack = empty_stack
        self.registers[reg].set_bytes(from_stack)

    def push_stack(self, reg):
        reg, _ = self.decode_reg(reg)
        high_part = self.registers[reg].get_byte(1)  # Czesc starsza
        low_part = self.registers[reg].get_byte(0)  # Czesc mlodsza

        self.stack.append(high_part+low_part)

    def interrupt_21H(self):
        ax_H_reg = self.show_register_int('AXH')

        if ax_H_reg == 1:
            # pobranie znaku ASCII
            self.int_21H_1()
        elif ax_H_reg == 2:
            # wyswietlenie znaku
            self.int_21H_2()
        elif ax_H_reg == 11:
            # sprawdzenie czy jest dostepny znak (wcisniety przycisk)
            self.int_21H_B()
        elif ax_H_reg == 42:
            # wpisanie daty do rejestrow
            self.int_21H_42()
        elif ax_H_reg == 44:
            # wpisanie czasu do rejestrow
            self.int_21H_44()
        elif ax_H_reg == 76:
            # wyjscie z programu
            self.int_21H_4C()

    def interrupt_33H(self):
        ax_reg = self.show_register_int('AX')

        if ax_reg == 1:
            # pokazanie kursora
            self.int_33H_1()
        elif ax_reg == 2:
            # ukrycie kursora
            self.int_33H_2()
        elif ax_reg == 3:
            # pobierz pozycje kursora
            self.int_33H_3()
        elif ax_reg == 4:
            # usaw pozycje kursora
            self.int_33H_4()

    def int_21H_4C(self):
        """
        przerwanie 21H, funkcja 4C  (76), Terminate Process With Return Code, zakoncz program

        Wejscie:
        AL = return code
        """
        ret_value = self.registers['AX'].get_int(0)
        exit(ret_value)


    def int_21H_1(self):
        """
        Wczytanie znaku z klawiatury i zapisanie ASCII do AXL
        :return:
        """

        ascii_char = self.GUI.get_key_value()  # ten do w wczytania
        self.registers['AX'].move_into(ascii_char, 0, is_int=True)  # zapisanie kodu ascii do AXL

    def int_21H_2(self):
        """
        Wyswietlenie znaku, kod ASCII w DXL
        :return:
        """
        byte_DL = self.registers['DX'].get_byte(0)
        char_DL = byte_DL.decode("ascii")  # zdekodowany znak do wyswietlenia
        self.GUI.set_output(char_DL)

    def int_21H_B(self):
        """
        INT 21H, B (11) Check Standard Input Status, Sprawdzenie czy klawisz jest wcisniety

        Wyjscie:
        AL = 00h, if no character available,
        AL = FFh, if character is available
        """

        char_present = self.GUI.is_key_pressed()

        if char_present:
            self.registers['AX'].move_into(255, 0, is_int=True)
        else:
            self.registers['AX'].move_into(0, 0, is_int=True)

    def int_21H_42(self):
        """
        przerwanie 21H, funkcja 2Ah (42), Get System Date

        AL         Day of the week (0 - 6; 0 = Sunday)
        CX         Year (1980 - 2099)
        DH         Month (1 - 12)
        DL         Day (1 - 31)
        :return:
        """
        date_now = datetime.datetime.now()

        year = date_now.year
        month = date_now.month
        day = date_now.day
        weekday = (datetime.datetime.today().weekday()) % 6  # 0 - niedziela

        self.registers['AX'].move_into(weekday, 0, is_int=True)
        self.registers['CX'].set_bytes(year, is_int=True)
        self.registers['DX'].move_into(month, 1, is_int=True)
        self.registers['DX'].move_into(day, 0, is_int=True)


    def int_21H_44(self):
        """
        przerwanie 21H, funkcja 2Ch  (44), Get System Time

        CH         Hour (0 - 23)
        CL         Minutes (0 - 59)
        DH         Seconds (0 - 59)
        DL         Hundredths of a second (0 - 99)
        :return:
        """
        time_now = datetime.datetime.now()

        hours = time_now.hour
        minutes = time_now.minute
        seconds = time_now.second
        hundreds_of_second = int(time_now.microsecond / 10000)  # dostepne microsekundy 0-1_000_000-1

        self.registers['CX'].move_into(hours, 1, is_int=True)
        self.registers['CX'].move_into(minutes, 0, is_int=True)
        self.registers['DX'].move_into(seconds, 1, is_int=True)
        self.registers['DX'].move_into(hundreds_of_second, 0, is_int=True)


    def int_33H_3(self):
        """
        przerwanie 33H, funkcja 3h  (3), Get Mouse Position and Button Status, pobierz pozycje kursora
        i stan przyciskow

        Wyjscie:
        CX = horizontal (X) position  (0..639)
        DX = vertical (Y) position  (0..199)
        BX = button status
        """
        horizontal_position, vertical_position = MainWindow.get_cursor_poisition()
        button_status = 1

        self.registers['CX'].set_bytes(horizontal_position, is_int=True)
        self.registers['DX'].set_bytes(vertical_position, is_int=True)
        self.registers['BX'].set_bytes(button_status, is_int=True)


    def int_33H_4(self):
        """
        przerwanie 33H, funkcja 4h  (4), Set Mouse Cursor Position, ustaw pozycje kursora
        Wejscie:
        CX = horizontal position
        DX = vertical position
        """
        horizontal_position = self.registers['CX'].get_int(-1)
        vertical_position = self.registers['DX'].get_int(-1)
        print(horizontal_position, vertical_position)
        MainWindow.set_cursor_poisition(horizontal_position, vertical_position)


    def int_33H_1(self):
        MainWindow.unsetCursor()
        self.show_cursor = True

    def int_33H_2(self):
        MainWindow.setCursor(Qt.BlankCursor)
        self.show_cursor = False

class Microprocessor(QtWidgets.QMainWindow):

    keyboard = QtCore.pyqtSignal(QtCore.QEvent)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.microprocessor = Microprocesor_cal(self)
        self.keyboard.connect(self.on_key)
        self.key = 53
        self.wait_key = False
        self.split_code = []
        self.line_no = 0
        self.cursor = QCursor()
        self.key_pressed = False

        self.ui.AXH.clicked.connect(self.show_registers_data)
        self.ui.Data.clicked.connect(self.show_registers_data)
        self.ui.AXL.clicked.connect(self.show_registers_data)
        self.ui.BXH.clicked.connect(self.show_registers_data)
        self.ui.BXL.clicked.connect(self.show_registers_data)
        self.ui.CXL.clicked.connect(self.show_registers_data)
        self.ui.CXH.clicked.connect(self.show_registers_data)
        self.ui.DXL.clicked.connect(self.show_registers_data)
        self.ui.DXH.clicked.connect(self.show_registers_data)
        self.ui.AXHo.clicked.connect(self.show_registers_data)
        self.ui.AXLo.clicked.connect(self.show_registers_data)
        self.ui.BXHo.clicked.connect(self.show_registers_data)
        self.ui.BXLo.clicked.connect(self.show_registers_data)
        self.ui.CXLo.clicked.connect(self.show_registers_data)
        self.ui.CXHo.clicked.connect(self.show_registers_data)
        self.ui.DXLo.clicked.connect(self.show_registers_data)
        self.ui.DXHo.clicked.connect(self.show_registers_data)
        self.ui.Data.clicked.connect(self.show_registers_data)
        self.ui.AX.clicked.connect(self.show_registers_data)
        self.ui.BX.clicked.connect(self.show_registers_data)
        self.ui.CX.clicked.connect(self.show_registers_data)
        self.ui.DX.clicked.connect(self.show_registers_data)
        self.ui.AXo.clicked.connect(self.show_registers_data)
        self.ui.BXo.clicked.connect(self.show_registers_data)
        self.ui.CXo.clicked.connect(self.show_registers_data)
        self.ui.DXo.clicked.connect(self.show_registers_data)
        self.ui.Operation.activated.connect(self.selected_operation)

        self.ui.AddStep.clicked.connect(self.add_step)
        self.ui.Execute.clicked.connect(self.execute_all)
        self.ui.LoadFile.clicked.connect(self.load_from_file)
        self.ui.Save.clicked.connect(self.save_to_file)
        self.ui.DeleteProgram.clicked.connect(self.delete_program)
        self.ui.DeleteLine.clicked.connect(self.delete_line)
        self.ui.StepByStep.clicked.connect(self.step_by_step_execution)

        self.show()

    def keyReleaseEvent(self, event):
        super(Microprocessor, self).keyReleaseEvent(event)
        self.keyboard.emit(event)

    def is_key_pressed(self):
        return self.key_pressed

    def on_key(self, event):
        if event.type() == QtCore.QEvent.KeyRelease:
            self.key = ord(chr(event.key()).lower())
            self.wait_key = False
            self.key_pressed = event.isAutoRepeat()

    def get_key_value(self):
        return self.key

    def get_cursor_poisition(self):
        return self.cursor.pos().x(), self.cursor.pos().y()

    def set_cursor_poisition(self, x, y):
        return self.cursor.setPos(x, y)

    def set_output(self, char):
        self.ui.output.setText(char)

    def add_step(self):
        first, second = self.register_choosing()
        operation = self.ui.Operation.currentText()
        REG = ["AX", "BX", "CX", "DX"]
        if operation == "INT21":
            self.split_code.append([operation])
        elif operation == "INT33":
            self.split_code.append([operation])
        elif operation == "POP":
            if second in REG:
                self.split_code.append([operation, second])
        elif operation == "PUSH":
            if first in REG:
                self.split_code.append([operation, first])
        elif first not in REG and second not in REG:
            if self.ui.Data.isChecked() == True and first and operation:
                if self.ui.DataToRegister.text().isnumeric():
                    if int(self.ui.DataToRegister.text()) > 255:
                        self.ui.DataToRegister.setText("255")
                    elif int(self.ui.DataToRegister.text()) >= 0:
                     self.split_code.append([operation, first,  self.ui.DataToRegister.text()])
                else:
                    self.ui.DataToRegister.setText("")
            if first and second and operation:
                self.split_code.append([operation, first, second])
        elif first in REG and (second in REG or self.ui.Data.isChecked() == True):
            if self.ui.Data.isChecked() == True and first and operation:
                if self.ui.DataToRegister.text().isnumeric():
                    if int(self.ui.DataToRegister.text()) > 65535:
                        self.ui.DataToRegister.setText("65535")
                    elif int(self.ui.DataToRegister.text()) >= 0:
                     self.split_code.append([operation, first,  self.ui.DataToRegister.text()])
                else:
                    self.ui.DataToRegister.setText("")
            if first and second and operation:
                self.split_code.append([operation, first, second])
        self.show_program()

    def register_choosing(self):
        first = ''
        second = ''
        if self.ui.AXH.isChecked()==True:
            second = 'AXH'
        elif self.ui.AXL.isChecked()==True:
            second = 'AXL'
        elif self.ui.BXH.isChecked()==True:
            second = 'BXH'
        elif self.ui.BXL.isChecked()==True:
            second = 'BXL'
        elif self.ui.CXL.isChecked()==True:
            second = 'CXL'
        elif self.ui.CXH.isChecked()==True:
            second = 'CXH'
        elif self.ui.DXH.isChecked()==True:
            second = 'DXH'
        elif self.ui.DXL.isChecked()==True:
            second = 'DXL'
        elif self.ui.AX.isChecked()==True:
            second = 'AX'
        elif self.ui.BX.isChecked()==True:
            second = 'BX'
        elif self.ui.CX.isChecked()==True:
            second = 'CX'
        elif self.ui.DX.isChecked()==True:
            second = 'DX'
        if self.ui.AXHo.isChecked()==True:
            first = 'AXH'
        elif self.ui.AXLo.isChecked()==True:
            first = 'AXL'
        elif self.ui.BXHo.isChecked()==True:
            first = 'BXH'
        elif self.ui.BXLo.isChecked()==True:
            first = 'BXL'
        elif self.ui.CXLo.isChecked()==True:
            first = 'CXL'
        elif self.ui.CXHo.isChecked()==True:
            first = 'CXH'
        elif self.ui.DXHo.isChecked()==True:
            first = 'DXH'
        elif self.ui.DXLo.isChecked()==True:
            first = 'DXL'
        elif self.ui.AXo.isChecked()==True:
            first = 'AX'
        elif self.ui.BXo.isChecked()==True:
            first = 'BX'
        elif self.ui.CXo.isChecked()==True:
            first = 'CX'
        elif self.ui.DXo.isChecked()==True:
            first = 'DX'
        return first, second

    def show_program(self):
        commands = ""
        i = 0
        for line in self.split_code:
            if len(line) == 3:
                commands = "{}. ".format(i).join((commands, " ".join((line[0],", ".join((line[1], line[2] + "\n"))))))
            elif len(line) == 2:
                commands = "{}. ".format(i).join((commands, " ".join((line[0], line[1] + "\n"))))
            elif len(line) == 1:
                commands = "{}. ".format(i).join((commands, line[0] + "\n"))
            i += 1

        self.ui.textBrowser.setText(commands)

    def selected_operation(self):

        if self.ui.Operation.currentText() == 'ADD':
            self.ui.textBrowser_2.setText('ADD R1, R2\n\n'
                                          'Dodanie zawartości dwóch rejestrów i zapisanie wyniku do R1.\n\n'
                                          'Możliwe jest działanie na całych rejestrach (16 bitów) lub ich połówkach. R2'
                                          ' może być liczbą w odpowiednim zakresie')
        elif self.ui.Operation.currentText() == 'SUB':
            self.ui.textBrowser_2.setText('SUB R1, R2\n\n'
                                          'Odjęcie zawartości rejestru R2 od R1 i zapisanie wyniku do R1.\n\n'
                                          'Możliwe jest działanie na całych rejestrach (16 bitów) lub ich połówkach. R2'
                                          ' może być liczbą w odpowiednim zakresie')
        elif self.ui.Operation.currentText() == 'MOV':
            self.ui.textBrowser_2.setText('MOVE R1, R2\n\n'
                                          'Przesłanie zawartości rejestru R2 od R1.\n\n'
                                          'Możliwe jest działanie na całych rejestrach (16 bitów) lub ich połówkach. R2'
                                          ' może być liczbą w odpowiednim zakresie')
        elif self.ui.Operation.currentText() == 'PUSH':
            self.ui.textBrowser_2.setText('PUSH R1 \n\n'
                                          'Zapisanie zawartości rejestru R1 na stos. R1 musi być rejestrem 16-bitowym')
        elif self.ui.Operation.currentText() == 'POP':
            self.ui.textBrowser_2.setText('POP R1\n\n'
                                          'Zdjęcie pierwszej wartości ze stosu i zapisanie jej do rejestru R1.'
                                          ' R1 musi być rejestrem 16-bitowym')
        elif self.ui.Operation.currentText() == 'INT21':
            self.ui.textBrowser_2.setText("Przerwanie INT21H - funkcja przerwania wybierana jest w zależności od"
                                          " zawartości rejestru AXH. "
                                          "Numery przerwań są podane w systemie dziesiętnym\n\n"
                                          
                                          "Dostępne funkcje:"
                                          "\nAXH = 1\n Wczytanie znaku z klawiatury i zapisanie kodu ASCII\n"
                                          "Wyjście: \nAXL - kod ASCII\n"
                                          ""
                                          "\n\nAXH = 2\nWyświetlenie znaku, kod ASCII w DXL. Znak wyświetla się w "
                                          "przygotowanym miejscu.\n"
                                          "Wejście: \nDXL - kod ASCII\n"
                                          
                                          "\n\nAXH = 11\nSprawdzenie czy klawisz jest wciśniety\n"
                                          "\nWyjście: \n"
                                          "AXL = 00h, jeśli żaden klawisz nie jest wciśnięty\n"
                                          "AXL = FFh, jeśli jakiś klawisz jest wciśnięty\n"
                                          
                                          "\n\nAXH = 42\nSprawdzenie daty\n"
                                          "Wyjście:\n"
                                          "AXL - dzień tygodnia (0-6), 0 - niedziela\n"
                                          "CX - rok\n"
                                          "DXH - miesiąc (1-12)\n"
                                          "DXL - dzień\n"

                                          "\n\nAXH = 44\nSprawdzenie czasu\n"
                                          "Wyjście:\n"
                                          "CH - godzina (0-23)\n"
                                          "CL - minuta\n"
                                          "DH - sekunda\n"
                                          "DL - setna sekundy\n"

                                          "\n\nAXH = 76\nZakoncz program i zwróć konkretną wartość\n"
                                          "Wejście:\n"
                                          "AL - zwracana wartość\n"
                                          )

        elif self.ui.Operation.currentText() == 'INT33':
            self.ui.textBrowser_2.setText("INT33 - funkcja przerwania wybierana jest w zależności od"
                                          " zawartości rejestru AX. "
                                          "Numery przerwań są podane w systemie dziesiętnym\n\n"
                                          
                                          "Dostępne funkcje:\n"
                                          "\nAX = 1\nPokazanie kursora\n"

                                          "\n\nAX = 2\nUkrycie kursora"
                                          
                                          "\n\nAX = 3\nPobierz pozycję kursora\n"
                                          "\nWyjście: \n"
                                          "CX - pozycja pozioma - w X\n"
                                          "DX - pozycja pozioma - w Y\n"
                                          "BX - przycisk\n"

                                          "\n\nAX = 4\nUstaw pozycję kursora\n"
                                          "\nWejscie: \n"
                                          "CX - pozycja pozioma - w X\n"
                                          "DX - pozycja pozioma - w Y\n"
                                          )

    def show_registers_data(self):
        first, second = self.register_choosing()
        if self.ui.Data.isChecked() == True and second:
            self.ui.OutputData.setText(self.ui.DataToRegister.text())
            self.ui.InputData.setText(str(self.microprocessor.show_register_int(second)))
        if first and second:
            self.ui.InputData.setText(str(self.microprocessor.show_register_int(second)))
            self.ui.OutputData.setText(str(self.microprocessor.show_register_int(first)))

    def load_from_file(self):
        """
        Zaladowanie kodu z pliku o nazwie file_name i zapisanie go do listy split_code (z instrukcjami rozdzielonymi
        od argumentów)
        """
        file_browser = FileBrowser()
        file_browser.openFileNameDialog()
        filename = file_browser.file
        self.delete_program()
        file = open(filename, 'r')
        lines = file.readlines()
        for line in lines:
            split_line = re.split(' |, |;|\n', line)
            split_line = split_line[:3]
            if split_line[-1] == '':
                split_line.pop()
            if split_line[-1] == '':
                split_line.pop()
            self.split_code.append(split_line)
        file.close()

        self.show_program()

    def save_to_file(self):
        file_browser = FileBrowser()
        file_browser.saveFileDialog()
        filename = file_browser.file
        file = open(filename, 'w')
        for line in self.split_code:
            if len(line) == 3:
                file.write(line[0] + " " + line[1] + ", " + line[2] + "\n")
            elif len(line) == 2:
                file.write(line[0] + " " + line[1] + "\n")
            elif len(line) == 1:
                file.write(line[0] + "\n")
        file.close()

    def execute_all(self):
        """
        Wykonanie całego kodu
        """
        if self.wait_key is False:
            for line in self.split_code:
                self.microprocessor.ex_instruction(line)
            self.show_registers_data()
            self.show_program()

    def step_by_step_execution(self):

        if self.line_no >= len(self.split_code):
            self.line_no = 0
            self.ui.StepLine.setText(str(self.line_no))
            return

        if self.wait_key is False:

            line = self.split_code[self.line_no]
            self.microprocessor.ex_instruction(line)
            self.line_no += 1
            self.ui.StepLine.setText(str(self.line_no))

            if self.line_no < len(self.split_code):
                if self.split_code[self.line_no] == ['INT21'] and str(self.microprocessor.show_register_int("AXH")) == '1':
                    self.wait_key = True
            self.show_registers_data()
            self.show_program()

    def delete_program(self):
        self.split_code = []
        self.show_program()

    def delete_line(self):
        if self.ui.LineNo.text().isnumeric():
            deleting_line = int(self.ui.LineNo.text())
            if deleting_line >= 0 and deleting_line <= len(self.split_code):
                self.split_code.pop(deleting_line)
        self.ui.LineNo.setText("")
        self.show_program()




app = QtWidgets.QApplication(sys.argv)
MainWindow = Microprocessor()
sys.exit(app.exec_())
