CREATE TABLE KATEGORIE (
    id_kategorii    INT PRIMARY KEY AUTO_INCREMENT,
    nazwa           VARCHAR(50) NOT NULL UNIQUE,
    cena_za_dobe    DECIMAL(10,2) NOT NULL CHECK (cena_za_dobe > 0),
    liczba_osob     INT NOT NULL CHECK (liczba_osob > 0),
    opis            TEXT,

    INDEX idx_kategorie_nazwa (nazwa)
);

-- tabela pokoi
CREATE TABLE POKOJE (
    id_pokoju       INT PRIMARY KEY AUTO_INCREMENT,
    numer_pokoju    VARCHAR(10) NOT NULL UNIQUE,
    id_kategorii    INT NOT NULL,
    pietro          INT NOT NULL CHECK (pietro >= 0),
    status          ENUM('dostepny', 'zajety', 'w_remoncie', 'wylaczony')
                    DEFAULT 'dostepny',

    -- kategoria pokoju
    CONSTRAINT fk_pokoje_kategorie
        FOREIGN KEY (id_kategorii) REFERENCES KATEGORIE(id_kategorii)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    INDEX idx_pokoje_kategoria (id_kategorii),
    INDEX idx_pokoje_status (status)
);

-- tabela goscie
CREATE TABLE GOSCIE (
    id_goscia       INT PRIMARY KEY AUTO_INCREMENT,
    imie            VARCHAR(50) NOT NULL,
    nazwisko        VARCHAR(50) NOT NULL,
    email           VARCHAR(100) UNIQUE,
    telefon         VARCHAR(20),
    pesel           CHAR(11) UNIQUE,
    adres           TEXT,
    data_rejestracji DATE DEFAULT (CURRENT_DATE),

    INDEX idx_goscie_nazwisko (nazwisko),
    INDEX idx_goscie_email (email)
);

-- tabela rezerwacji
CREATE TABLE REZERWACJE (
    id_rezerwacji   INT PRIMARY KEY AUTO_INCREMENT,
    id_goscia       INT NOT NULL,
    id_kategorii    INT NOT NULL,
    data_od         DATE NOT NULL,
    data_do         DATE NOT NULL,
    liczba_pokoi    INT NOT NULL DEFAULT 1 CHECK (liczba_pokoi > 0),
    status          ENUM('oczekujaca', 'potwierdzona', 'zrealizowana',
                         'anulowana') DEFAULT 'oczekujaca',
    data_zlozenia   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uwagi           TEXT,

    -- walidacja daty rezerwacji
    CONSTRAINT chk_daty_rezerwacji CHECK (data_do > data_od),

    -- klucze obce
    CONSTRAINT fk_rezerwacje_goscie
        FOREIGN KEY (id_goscia) REFERENCES GOSCIE(id_goscia)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_rezerwacje_kategorie
        FOREIGN KEY (id_kategorii) REFERENCES KATEGORIE(id_kategorii)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    INDEX idx_rezerwacje_goscie (id_goscia),
    INDEX idx_rezerwacje_kategorie (id_kategorii),
    INDEX idx_rezerwacje_daty (data_od, data_do),
    INDEX idx_rezerwacje_status (status)
);

-- do przechowywania przydzialu pokoi
CREATE TABLE PRZYDZIELENIA (
    id_przydzielenia    INT PRIMARY KEY AUTO_INCREMENT,
    id_rezerwacji       INT NOT NULL,
    id_pokoju           INT NOT NULL,
    data_zameldowania   DATE NOT NULL,
    data_wymeldowania   DATE NOT NULL,
    kwota               DECIMAL(10,2) NOT NULL CHECK (kwota >= 0),
    status              ENUM('zaplanowane', 'zameldowany', 'wymeldowany',
                             'anulowane') DEFAULT 'zaplanowane',

    -- walidacja daty przydzielenia pokoju i zameldowania
    CONSTRAINT chk_daty_przydzielenia
        CHECK (data_wymeldowania > data_zameldowania),

    CONSTRAINT fk_przydzielenia_rezerwacje
        FOREIGN KEY (id_rezerwacji) REFERENCES REZERWACJE(id_rezerwacji)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_przydzielenia_pokoje
        FOREIGN KEY (id_pokoju) REFERENCES POKOJE(id_pokoju)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    INDEX idx_przydzielenia_rezerwacja (id_rezerwacji),
    INDEX idx_przydzielenia_pokoj (id_pokoju),
    INDEX idx_przydzielenia_daty (data_zameldowania, data_wymeldowania),
    INDEX idx_przydzielenia_status (status)
);