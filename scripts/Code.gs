/**
 * Kesha Finance Tracker — Google Sheets Apps Script
 *
 * Актуальная версия под текущую схему проекта:
 *   Telegram bot (Python) + PWA (Next.js/Vercel) + Fly.io
 *
 * Как использовать:
 *   1. Открыть Google Таблицу → Расширения → Apps Script
 *   2. Вставить этот файл в Code.gs
 *   3. Запустить setupSheetsSafe() — безопасно, данные не удаляются
 *   4. Дать разрешения при запросе
 *
 * ⚠️ НЕ запускай resetSheetsDangerously() на рабочей таблице — удалит все данные.
 */

// ============================================================
// CONFIG
// ============================================================

// Цвета по умолчанию для автозаполнения Categories.
// При seedDefaultCategoryColors() записываются в лист Categories.
// Дальше applyColorsToAll() и onEdit() читают цвета из листа, а не отсюда.
var DEFAULT_CATEGORY_COLORS = {
  // Расходы
  'Кофе':          '#5C4033',
  'Еда':           '#E65100',
  'Такси':         '#FFD600',
  'Одежда':        '#E91E63',
  'Красота':       '#F48FB1',
  'Подписки':      '#7C4DFF',
  'Дом':           '#795548',
  'Подарки':       '#FF4081',
  'Маркетплейсы':  '#00BCD4',
  'Здоровье':      '#4CAF50',
  'Развлечения':   '#FF9800',
  'Другое':        '#9E9E9E',

  // Доходы
  'Зарплата':      '#2E7D32',
  'Фриланс':       '#1B5E20',
  'Подарок':       '#FF4081',
  'Инвестиции':    '#0D47A1',
  'Возврат долга': '#4CAF50',
};

var DEFAULT_COLOR = '#F5F5F5';

// Хедеры листов — должны совпадать с bot/sheets.py
var TRANSACTIONS_HEADERS = [
  'Month',       // A
  'Date',        // B
  'Type',        // C
  'Amount UAH',  // D
  'Amount USD',  // E
  'Amount EUR',  // F
  'Category',    // G
  'AI Comment',  // H
  'Source',      // I
  'Account ID',  // J
  'Account Name',// K
  'Transfer ID'  // L
];

var BUDGET_HEADERS = ['Month', 'Category', 'Limit', 'Type'];
var CATEGORIES_HEADERS = ['Type', 'Name', 'Color'];
var SETTINGS_HEADERS = ['Key', 'Value'];
var RULES_HEADERS = ['Pattern', 'Category', 'Type', 'Priority'];
var ACCOUNTS_HEADERS = [
  'ID',
  'Name',
  'Type',
  'Currency',
  'Balance',
  'Source',
  'Active',
  'CreatedAt',
  'UpdatedAt'
];

var RECURRING_HEADERS = [
  'ID',
  'Title',
  'Type',
  'Amount',
  'Currency',
  'OriginalAmount',
  'OriginalCurrency',
  'EstimatedUAH',
  'AmountMode',
  'Category',
  'DefaultAccountID',
  'DefaultAccountName',
  'PaymentOptions',
  'Frequency',
  'DayOfMonth',
  'DueDay',
  'GraceUntilDay',
  'NextRunDate',
  'LastRunDate',
  'Status',
  'CreatedAt',
  'UpdatedAt',
  'Notes',
  'LastAction'
];

// ============================================================
// SAFE SETUP — не удаляет существующие данные
// ============================================================

/**
 * Безопасный alert: показывает UI-диалог если доступен, иначе пишет в Logger.
 * setupSheetsSafe() и applyColorsToAll() могут вызываться из контекстов
 * без UI (Apps Script editor), где getUi() выбрасывает исключение.
 */
function safeAlert(message) {
  try {
    SpreadsheetApp.getUi().alert(message);
  } catch (e) {
    Logger.log(message);
  }
}

/**
 * Показывает confirm-диалог YES/NO.
 * Возвращает true если YES, false в любом другом случае (включая отсутствие UI).
 */
function safeConfirm(title, body) {
  try {
    var ui = SpreadsheetApp.getUi();
    return ui.alert(title, body, ui.ButtonSet.YES_NO) === ui.Button.YES;
  } catch (e) {
    Logger.log('safeConfirm failed — no UI context: ' + title);
    return false;
  }
}

/**
 * Безопасная настройка всех листов.
 * Создаёт недостающие листы, добавляет недостающие заголовки,
 * расширяет до актуальной схемы. НЕ удаляет строки с данными.
 */
function setupSheetsSafe() {
  ensureTransactionsSheet();
  ensureBudgetsSheet();
  ensureCategoriesSheet();
  ensureSettingsSheet();
  ensureRulesSheet();
  ensureAccountsSheet();
  ensureRecurringSheet();

  seedDefaultCategoryColors();
  applyColorsToAll();

  safeAlert(
    '✅ Настройка Kesha завершена!\n\n' +
    'Проверены/созданы листы:\n' +
    '• Transactions (A-L, 12 колонок)\n' +
    '• Budgets\n' +
    '• Categories (Type + Name + Color)\n' +
    '• Settings\n' +
    '• Rules\n' +
    '• Accounts (9 колонок)\n' +
    '• Recurring (24 колонки)\n\n' +
    'Существующие данные сохранены.'
  );
}

/**
 * Обратно-совместимый alias.
 * Вызывает setupSheetsSafe — НЕ удаляет данные.
 */
function setupSheets() {
  setupSheetsSafe();
}

// ============================================================
// DANGEROUS RESET — только для новой пустой таблицы
// ============================================================

/**
 * Полный сброс всех листов Kesha.
 * ⚠️ Удаляет ВСЕ данные в Transactions, Budgets, Categories,
 *    Settings, Rules и Accounts.
 * Использовать ТОЛЬКО для новой пустой таблицы.
 */
function resetSheetsDangerously() {
  var confirmed = safeConfirm(
    '⚠️ Полный сброс таблицы Kesha?',
    'Будут очищены ВСЕ данные в листах:\n' +
    'Transactions, Budgets, Categories, Settings, Rules, Accounts, Recurring.\n\n' +
    'Это действие НЕОБРАТИМО.\n' +
    'Используйте только для новой пустой таблицы.\n\n' +
    'Продолжить?'
  );

  if (!confirmed) {
    Logger.log('resetSheetsDangerously: отменено (нет UI-подтверждения или пользователь нажал NO).');
    return;
  }

  createOrResetSheet('Transactions', TRANSACTIONS_HEADERS);
  createOrResetSheet('Budgets', BUDGET_HEADERS);
  createOrResetSheet('Categories', CATEGORIES_HEADERS);
  createOrResetSheet('Settings', SETTINGS_HEADERS);
  createOrResetSheet('Rules', RULES_HEADERS);
  createOrResetSheet('Accounts', ACCOUNTS_HEADERS);
  createOrResetSheet('Recurring', RECURRING_HEADERS);

  formatAllCoreSheets();

  safeAlert('✅ Таблица сброшена. Все листы созданы заново с заголовками.');
}

// ============================================================
// SHEET ENSURE FUNCTIONS
// ============================================================

function ensureTransactionsSheet() {
  var sheet = ensureSheetWithHeaders('Transactions', TRANSACTIONS_HEADERS);
  formatTransactionsSheet(sheet);
}

function ensureBudgetsSheet() {
  var sheet = ensureSheetWithHeaders('Budgets', BUDGET_HEADERS);
  formatBudgetsSheet(sheet);
}

function ensureCategoriesSheet() {
  var sheet = ensureSheetWithHeaders('Categories', CATEGORIES_HEADERS);

  // Миграция: старый заголовок 'Category' → 'Name'
  var currentB1 = sheet.getRange(1, 2).getValue();
  if (currentB1 === 'Category') {
    sheet.getRange(1, 2).setValue('Name');
  }

  // Миграция: если колонка Color пустая в заголовке, записать
  var currentC1 = sheet.getRange(1, 3).getValue();
  if (!currentC1 || String(currentC1).trim() === '') {
    sheet.getRange(1, 3).setValue('Color');
  }

  formatCategoriesSheet(sheet);
}

function ensureSettingsSheet() {
  var sheet = ensureSheetWithHeaders('Settings', SETTINGS_HEADERS);
  formatSettingsSheet(sheet);
}

function ensureRulesSheet() {
  var sheet = ensureSheetWithHeaders('Rules', RULES_HEADERS);
  formatRulesSheet(sheet);
}

function ensureAccountsSheet() {
  var sheet = ensureSheetWithHeaders('Accounts', ACCOUNTS_HEADERS);
  formatAccountsSheet(sheet);
}

function ensureRecurringSheet() {
  var sheet = ensureSheetWithHeaders('Recurring', RECURRING_HEADERS);
  formatRecurringSheet(sheet);
}

function formatAllCoreSheets() {
  formatTransactionsSheet(getOrCreateSheet('Transactions'));
  formatBudgetsSheet(getOrCreateSheet('Budgets'));
  formatCategoriesSheet(getOrCreateSheet('Categories'));
  formatSettingsSheet(getOrCreateSheet('Settings'));
  formatRulesSheet(getOrCreateSheet('Rules'));
  formatAccountsSheet(getOrCreateSheet('Accounts'));
  formatRecurringSheet(getOrCreateSheet('Recurring'));
}

// ============================================================
// FORMATTERS
// ============================================================

function formatHeader(sheet, width) {
  sheet.getRange(1, 1, 1, width)
    .setFontWeight('bold')
    .setBackground('#1e293b')
    .setFontColor('#fbbf24');
  sheet.setFrozenRows(1);
}

/**
 * Сбросить стили строк данных: белый фон, чёрный текст, normal weight.
 * Не трогает header row 1.
 */
function resetDataRowsFormatting(sheet, width) {
  var maxRows = sheet.getMaxRows();
  if (maxRows <= 1) return;

  sheet.getRange(2, 1, maxRows - 1, width)
    .setBackground('#ffffff')
    .setFontColor('#000000')
    .setFontWeight('normal');
}

function formatTransactionsSheet(sheet) {
  formatHeader(sheet, TRANSACTIONS_HEADERS.length);
  resetDataRowsFormatting(sheet, TRANSACTIONS_HEADERS.length);

  // Валидация Type (C)
  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['income', 'expense'], true)
    .build();
  sheet.getRange('C2:C').setDataValidation(typeRule);

  sheet.getRange('B2:B').setNumberFormat('dd.mm.yyyy');
  sheet.getRange('D2:F').setNumberFormat('#,##0.00');

  sheet.setColumnWidth(1, 100);   // Month
  sheet.setColumnWidth(2, 90);    // Date
  sheet.setColumnWidth(3, 80);    // Type
  sheet.setColumnWidth(4, 100);   // Amount UAH
  sheet.setColumnWidth(5, 100);   // Amount USD
  sheet.setColumnWidth(6, 100);   // Amount EUR
  sheet.setColumnWidth(7, 150);   // Category
  sheet.setColumnWidth(8, 250);   // AI Comment
  sheet.setColumnWidth(9, 200);   // Source
  sheet.setColumnWidth(10, 140);  // Account ID
  sheet.setColumnWidth(11, 160);  // Account Name
  sheet.setColumnWidth(12, 220);  // Transfer ID
}

function formatBudgetsSheet(sheet) {
  formatHeader(sheet, BUDGET_HEADERS.length);
  resetDataRowsFormatting(sheet, BUDGET_HEADERS.length);

  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['budget', 'limit'], true)
    .build();
  sheet.getRange('D2:D').setDataValidation(typeRule);

  sheet.setColumnWidth(1, 100);
  sheet.setColumnWidth(2, 150);
  sheet.setColumnWidth(3, 100);
  sheet.setColumnWidth(4, 80);
}

function formatCategoriesSheet(sheet) {
  formatHeader(sheet, CATEGORIES_HEADERS.length);
  resetDataRowsFormatting(sheet, CATEGORIES_HEADERS.length);

  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['expense', 'income'], true)
    .build();
  sheet.getRange('A2:A').setDataValidation(typeRule);

  // Подсказка для колонки Color
  sheet.getRange(1, 3).setNote('HEX color, example #BBDEFB');

  sheet.setColumnWidth(1, 100);
  sheet.setColumnWidth(2, 250);
  sheet.setColumnWidth(3, 120);
}

function formatSettingsSheet(sheet) {
  formatHeader(sheet, SETTINGS_HEADERS.length);
  resetDataRowsFormatting(sheet, SETTINGS_HEADERS.length);
  sheet.setColumnWidth(1, 200);
  sheet.setColumnWidth(2, 250);
}

function formatRulesSheet(sheet) {
  formatHeader(sheet, RULES_HEADERS.length);
  resetDataRowsFormatting(sheet, RULES_HEADERS.length);

  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['expense', 'income', 'any'], true)
    .build();
  sheet.getRange('C2:C').setDataValidation(typeRule);

  sheet.getRange('D2:D').setNumberFormat('0');

  sheet.setColumnWidth(1, 220); // Pattern
  sheet.setColumnWidth(2, 160); // Category
  sheet.setColumnWidth(3, 100); // Type
  sheet.setColumnWidth(4, 100); // Priority
}

function formatAccountsSheet(sheet) {
  formatHeader(sheet, ACCOUNTS_HEADERS.length);
  resetDataRowsFormatting(sheet, ACCOUNTS_HEADERS.length);

  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(
      ['cash', 'card', 'bank', 'mono', 'deposit', 'loan', 'debt', 'crypto', 'other'],
      true
    )
    .build();
  sheet.getRange('C2:C').setDataValidation(typeRule);

  var currencyRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['UAH', 'USD', 'EUR', 'USDT'], true)
    .build();
  sheet.getRange('D2:D').setDataValidation(currencyRule);

  var activeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['TRUE', 'FALSE'], true)
    .build();
  sheet.getRange('G2:G').setDataValidation(activeRule);

  sheet.getRange('E2:E').setNumberFormat('#,##0.00');

  sheet.setColumnWidth(1, 220); // ID
  sheet.setColumnWidth(2, 160); // Name
  sheet.setColumnWidth(3, 100); // Type
  sheet.setColumnWidth(4, 90);  // Currency
  sheet.setColumnWidth(5, 120); // Balance
  sheet.setColumnWidth(6, 120); // Source
  sheet.setColumnWidth(7, 90);  // Active
  sheet.setColumnWidth(8, 160); // CreatedAt
  sheet.setColumnWidth(9, 160); // UpdatedAt
}

function formatRecurringSheet(sheet) {
  formatHeader(sheet, RECURRING_HEADERS.length);
  resetDataRowsFormatting(sheet, RECURRING_HEADERS.length);

  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['expense', 'income'], true)
    .build();
  sheet.getRange('C2:C').setDataValidation(typeRule);

  var currencyRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['UAH', 'USD', 'EUR', 'USDT'], true)
    .build();
  sheet.getRange('E2:E').setDataValidation(currencyRule);
  sheet.getRange('G2:G').setDataValidation(currencyRule);

  var modeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['fixed', 'variable', 'fx'], true)
    .build();
  sheet.getRange('I2:I').setDataValidation(modeRule);

  var freqRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['monthly', 'weekly', 'daily'], true)
    .build();
  sheet.getRange('N2:N').setDataValidation(freqRule);

  var statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['active', 'paused', 'deleted'], true)
    .build();
  sheet.getRange('T2:T').setDataValidation(statusRule);

  sheet.getRange('D2:D').setNumberFormat('#,##0.00');
  sheet.getRange('F2:F').setNumberFormat('#,##0.00');
  sheet.getRange('H2:H').setNumberFormat('#,##0.00');
  sheet.getRange('O2:Q').setNumberFormat('0');

  sheet.setColumnWidth(1, 200);
  sheet.setColumnWidth(2, 180);
  sheet.setColumnWidth(3, 80);
  sheet.setColumnWidth(4, 100);
  sheet.setColumnWidth(5, 80);
  sheet.setColumnWidth(6, 110);
  sheet.setColumnWidth(7, 100);
  sheet.setColumnWidth(8, 110);
  sheet.setColumnWidth(9, 100);
  sheet.setColumnWidth(10, 130);
  sheet.setColumnWidth(11, 140);
  sheet.setColumnWidth(12, 150);
  sheet.setColumnWidth(13, 200);
  sheet.setColumnWidth(14, 90);
  sheet.setColumnWidth(15, 90);
  sheet.setColumnWidth(16, 70);
  sheet.setColumnWidth(17, 80);
  sheet.setColumnWidth(18, 110);
  sheet.setColumnWidth(19, 110);
  sheet.setColumnWidth(20, 80);
  sheet.setColumnWidth(21, 140);
  sheet.setColumnWidth(22, 140);
  sheet.setColumnWidth(23, 250);
  sheet.setColumnWidth(24, 180);
}

// ============================================================
// AUTO FORMAT ON EDIT
// ============================================================

function onEdit(e) {
  if (!e) return;

  var sheet = e.source.getActiveSheet();
  if (sheet.getName() !== 'Transactions') return;

  var range = e.range;
  var row = range.getRow();
  var col = range.getColumn();

  // Пропускаем заголовок
  if (row === 1) return;

  // Пропускаем пустые строки
  var rowData = sheet.getRange(row, 1, 1, TRANSACTIONS_HEADERS.length).getValues()[0];
  if (!rowData.some(function(cell) { return cell !== '' && cell !== null && cell !== undefined; })) {
    return;
  }

  // Category (G) → красим строку A:L
  if (col === 7) {
    var category = range.getValue();
    var colors = getCategoryColorsFromSheet();
    var color = colors[category] || DEFAULT_COLOR;
    sheet.getRange(row, 1, 1, TRANSACTIONS_HEADERS.length).setBackground(color);
  }

  // Date (B) → Month (A)
  if (col === 2) {
    var dateValue = range.getValue();
    if (dateValue instanceof Date) {
      sheet.getRange(row, 1).setValue(
        Utilities.formatDate(dateValue, Session.getScriptTimeZone(), 'MMMM')
      );
    }
  }
}

// ============================================================
// MENU
// ============================================================

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🧮 Kesha')
    .addItem('⚙️ Безопасно настроить таблицу', 'setupSheetsSafe')
    .addItem('📊 Отчёт за месяц', 'generateMonthlyReport')
    .addItem('🎨 Применить цвета', 'applyColorsToAll')
    .addSeparator()
    .addItem('⚠️ Полный сброс таблицы', 'resetSheetsDangerously')
    .addToUi();
}

/**
 * Прочитать цвета категорий из листа Categories.
 * Возвращает объект { 'Кофе': '#5C4033', ... }.
 * Если листа нет или цвет не указан — категория не попадает в результат.
 */
function getCategoryColorsFromSheet() {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName('Categories');
  if (!sheet) return {};

  var data = sheet.getDataRange().getValues();
  var colors = {};

  for (var i = 1; i < data.length; i++) {
    var name = String(data[i][1] || '').trim();  // column B
    var color = String(data[i][2] || '').trim();  // column C
    if (name && color && /^#[0-9A-Fa-f]{6}$/.test(color)) {
      colors[name] = color;
    }
  }

  return colors;
}

/**
 * Заполнить пустые цвета в Categories из DEFAULT_CATEGORY_COLORS.
 * Существующие цвета не перезаписываются.
 */
function seedDefaultCategoryColors() {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName('Categories');
  if (!sheet) return;

  var data = sheet.getDataRange().getValues();
  var updated = 0;

  for (var i = 1; i < data.length; i++) {
    var name = String(data[i][1] || '').trim();
    var color = String(data[i][2] || '').trim();
    if (name && !color && DEFAULT_CATEGORY_COLORS[name]) {
      sheet.getRange(i + 1, 3).setValue(DEFAULT_CATEGORY_COLORS[name]);
      updated++;
    }
  }

  if (updated > 0) {
    Logger.log('seedDefaultCategoryColors: ' + updated + ' colours seeded.');
  }
}

function applyColorsToAll() {
  var sheet = SpreadsheetApp.getActive().getSheetByName('Transactions');
  if (!sheet) return;

  var colors = getCategoryColorsFromSheet();
  var data = sheet.getDataRange().getValues();
  var width = Math.max(TRANSACTIONS_HEADERS.length, sheet.getLastColumn());

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    // Пропускаем пустые строки
    if (!row.some(function(cell) { return cell !== '' && cell !== null && cell !== undefined; })) {
      continue;
    }
    var category = row[6];  // column G
    var color = colors[category] || DEFAULT_COLOR;
    if (category) {
      sheet.getRange(i + 1, 1, 1, width).setBackground(color);
    }
  }

  safeAlert('🎨 Цвета применены к ' + (data.length - 1) + ' строкам.');
}

// ============================================================
// REPORTS
// ============================================================

function generateMonthlyReport() {
  var ss = SpreadsheetApp.getActive();
  var transactions = ss.getSheetByName('Transactions');
  if (!transactions) return;

  var data = transactions.getDataRange().getValues();
  var now = new Date();
  var currentMonth = Utilities.formatDate(now, Session.getScriptTimeZone(), 'MMMM');

  var expensesByCategory = {};
  var incomeByCategory = {};
  var totalExpense = 0;
  var totalIncome = 0;
  var transfersTotal = 0;

  var seenTransfers = {};

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var month = row[0];
    var type = String(row[2] || '').toLowerCase();
    var amount = Number(row[3]) || 0;
    var category = row[6] || 'Другое';
    var transferId = row[11] || '';

    if (month !== currentMonth) continue;

    // Переводы (TransferID) не считаем как доходы/расходы.
    // Один перевод = две строки (expense + income) → считаем сумму только один раз.
    if (transferId) {
      if (!seenTransfers[transferId]) {
        seenTransfers[transferId] = true;
        transfersTotal += Math.abs(amount);
      }
      continue;
    }

    if (type === 'expense') {
      expensesByCategory[category] = (expensesByCategory[category] || 0) + Math.abs(amount);
      totalExpense += Math.abs(amount);
    } else if (type === 'income') {
      incomeByCategory[category] = (incomeByCategory[category] || 0) + Math.abs(amount);
      totalIncome += Math.abs(amount);
    }
  }

  var reportName = 'Report_' + currentMonth;
  var reportSheet = getOrCreateSheet(reportName);
  reportSheet.clear();

  reportSheet.getRange('A1').setValue('📊 Финансовый отчёт — ' + currentMonth + ' ' + now.getFullYear());
  reportSheet.getRange('A1:B1').merge();
  reportSheet.getRange('A1').setFontWeight('bold').setFontSize(14);

  var rowNum = 3;
  reportSheet.getRange('A' + rowNum).setValue('💰 Доходы').setFontWeight('bold');
  reportSheet.getRange('B' + rowNum).setValue(Number(totalIncome).toFixed(2) + ' UAH');
  rowNum++;

  for (var incCat in incomeByCategory) {
    reportSheet.getRange('A' + rowNum).setValue('   ' + incCat);
    reportSheet.getRange('B' + rowNum).setValue(Number(incomeByCategory[incCat]).toFixed(2));
    rowNum++;
  }

  rowNum++;
  reportSheet.getRange('A' + rowNum).setValue('💸 Расходы').setFontWeight('bold');
  reportSheet.getRange('B' + rowNum).setValue(Number(totalExpense).toFixed(2) + ' UAH');
  rowNum++;

  for (var expCat in expensesByCategory) {
    reportSheet.getRange('A' + rowNum).setValue('   ' + expCat);
    reportSheet.getRange('B' + rowNum).setValue(Number(expensesByCategory[expCat]).toFixed(2));
    rowNum++;
  }

  rowNum++;
  var balance = totalIncome - totalExpense;
  reportSheet.getRange('A' + rowNum).setValue('📈 Итого').setFontWeight('bold');
  reportSheet.getRange('B' + rowNum).setValue(Number(balance).toFixed(2) + ' UAH');
  reportSheet.getRange('A' + rowNum + ':B' + rowNum)
    .setFontWeight('bold')
    .setBackground(balance >= 0 ? '#E8F5E9' : '#FFEBEE');

  rowNum++;
  reportSheet.getRange('A' + rowNum).setValue('🔁 Переводы внутри счетов').setFontWeight('bold');
  reportSheet.getRange('B' + rowNum).setValue(Number(transfersTotal).toFixed(2) + ' UAH');

  reportSheet.setColumnWidth(1, 270);
  reportSheet.setColumnWidth(2, 160);

  safeAlert(
    '✅ Отчёт создан!\n\n' +
    'Лист: ' + reportName + '\n' +
    'Доход: +' + totalIncome.toFixed(0) + ' UAH\n' +
    'Расход: -' + totalExpense.toFixed(0) + ' UAH\n' +
    'Баланс: ' + (balance >= 0 ? '+' : '') + balance.toFixed(0) + ' UAH\n' +
    'Переводы: ' + transfersTotal.toFixed(0) + ' UAH'
  );
}

// ============================================================
// UTILITIES
// ============================================================

/**
 * Проверить и восстановить заголовки листа.
 *
 * Логика:
 *   1. Пустой лист → записать headers в строку 1.
 *   2. Строка 1 содержит корректные заголовки → дополнить недостающие
 *      (расширение схемы), существующие не трогать.
 *   3. Строка 1 НЕ похожа на заголовки (удалена/повреждена) →
 *      вставить новую строку 1, записать headers, данные сдвинуть вниз.
 *
 * Заголовки считаются валидными если:
 *   A1 == headers[0] И B1 == headers[1] И (headers.length >= 3 → C1 == headers[2]).
 */
function ensureSheetWithHeaders(name, headers) {
  var sheet = getOrCreateSheet(name);

  // Пустой лист — записываем все заголовки
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    return sheet;
  }

  // Проверяем, похожа ли строка 1 на заголовки
  var existing = sheet.getRange(1, 1, 1, Math.max(headers.length, 3)).getValues()[0];
  var a1 = existing[0] != null ? String(existing[0]).trim() : '';
  var b1 = existing[1] != null ? String(existing[1]).trim() : '';
  var c1 = existing[2] != null ? String(existing[2]).trim() : '';

  var headersValid = (
    a1 === String(headers[0]) &&
    b1 === String(headers[1])
  );
  if (headers.length >= 3) {
    headersValid = headersValid && (c1 === String(headers[2]));
  }

  if (headersValid) {
    // Строка 1 — валидные заголовки. Дописываем недостающие (расширение схемы).
    for (var i = 0; i < headers.length; i++) {
      if (!existing[i] || String(existing[i]).trim() === '') {
        sheet.getRange(1, i + 1).setValue(headers[i]);
      }
    }
    return sheet;
  }

  // Строка 1 повреждена (содержит данные вместо заголовков).
  // Вставляем новую строку 1 и пишем туда headers.
  // Данные сдвигаются вниз (с row 2), не удаляются.
  sheet.insertRowsBefore(1, 1);
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  // Применить стили: header тёмный, данные (row 2+) — обычные.
  // formatHeader + resetDataRowsFormatting сбрасывают стиль
  // сдвинутых данных, унаследовавших header-стиль.
  formatHeader(sheet, headers.length);
  resetDataRowsFormatting(sheet, headers.length);

  return sheet;
}

/**
 * Создаёт лист, очищает, пишет заголовки.
 * Используется ТОЛЬКО в resetSheetsDangerously().
 */
function createOrResetSheet(name, headers) {
  var sheet = getOrCreateSheet(name);
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  return sheet;
}

/**
 * Получить лист по имени или создать новый.
 */
function getOrCreateSheet(name) {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
